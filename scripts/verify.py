"""Run every study template end to end in a fresh temporary workspace with the free test model.

    python scripts/verify.py

Installs every package, copies the packages and templates into the workspace's Explore folder, uses each
template, publishes the configuration, starts a pilot for every condition and checks that the run completes
with every measure ok. Uses the app named by HNF_APP (see scripts/build.py).
"""

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import API, ROOT, install, workspace  # noqa: E402


def wait(client, run_id, seconds=900):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        run = client.get(f"{API}/runs/{run_id}").json()
        if run["status"] not in {"QUEUED", "INITIALIZING", "RUNNING"}:
            return run
        time.sleep(0.1)
    raise AssertionError(f"Run {run_id} did not finish in {seconds} seconds.")


def main():
    packages = sorted((ROOT / "packages").glob("*.hnf.json"))
    templates = sorted((ROOT / "templates").glob("*.template.json"))
    failures = 0
    with tempfile.TemporaryDirectory() as folder, workspace(folder) as client:
        install(client, packages)
        explore = Path(folder) / "explore"
        explore.mkdir(exist_ok=True)
        for path in packages + templates:
            shutil.copy(path, explore / path.name)
        for path in templates:
            template_id = path.name.removesuffix(".template.json")
            used = client.post(f"{API}/explore/templates/{template_id}/use")
            assert used.status_code == 201, (template_id, used.text)
            experiment = client.get(f"{API}/experiments/{used.json()['experiment_id']}").json()
            version = client.post(f"{API}/experiments/{experiment['id']}/versions", json={"revision": experiment["revision"]})
            assert version.status_code == 201, (template_id, version.text)
            for condition in json.loads(path.read_text())["spec"]["conditions"]:
                started = client.post(f"{API}/experiment-versions/{version.json()['id']}/pilot",
                                      json={"condition_id": condition["id"]},
                                      headers={"Idempotency-Key": f"verify-{template_id}-{condition['id']}"})
                assert started.status_code == 202, (template_id, condition["id"], started.text)
                run = wait(client, started.json()["run_ids"][0])
                metrics = run.get("metrics") or []
                ok = run["status"] == "COMPLETED" and metrics and all(item["status"] == "ok" for item in metrics)
                failures += not ok
                values = ", ".join(f"{item['id']}={item['value']} ({item['status']})" for item in metrics)
                print(f"{'PASS' if ok else 'FAIL'} {template_id} / {condition['id']}: {run['status']}; {values}"
                      + ("" if ok else f"; error: {run.get('error')}"), flush=True)
    print(f"{len(templates)} templates checked, {failures} failing runs.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
