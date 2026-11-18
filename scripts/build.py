"""Rebuild every package from sources/ and regenerate the study templates through the app.

    python scripts/build.py                 # packages and templates
    python scripts/build.py --packages-only

Needs a local checkout of the Human Not Found app (its Python environment runs this script). Point
HNF_APP at its folder if it is not at ../AUI-Team-Simulator/implementation/human-not-found-v2.

Packages: sources/<bundle_id>/component.py and manifest.json are packed with the app's SDK script
(human_not_found_build_pack/sdk/pack_python.py) into packages/<bundle_id>-<version>.hnf.json.

Templates: sources/templates.py defines each study. The script installs the packages in a temporary
workspace, saves and publishes each configuration, and writes the app's own Export as template result
to templates/<id>.template.json, so the template's package checksums match the packages.
"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("HNF_APP") or ROOT.parent / "AUI-Team-Simulator/implementation/human-not-found-v2")
AUTHOR = "Human Not Found"
API = "/api/v1"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_packages():
    pack = load(APP / "human_not_found_build_pack/sdk/pack_python.py", "pack_python")
    built = []
    for folder in sorted(path for path in (ROOT / "sources").iterdir() if (path / "manifest.json").exists()):
        bundle = pack.package(folder / "component.py", folder / "manifest.json")
        manifest = bundle["manifest"]
        out = ROOT / "packages" / f"{manifest['bundle_id']}-{manifest['version']}.hnf.json"
        out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
        built.append(out)
        print(out.relative_to(ROOT))
    return built


def workspace(folder):
    """A FastAPI test client on a fresh workspace with no Explore repository."""
    sys.path.insert(0, str(APP))
    os.environ.update(HNF_EXPLORE_URL="", HNF_EXPLORE_DIR=str(Path(folder) / "explore"))
    from fastapi.testclient import TestClient
    from hnf.app import create_app
    return TestClient(create_app(Path(folder) / "workspace.db"))


def install(client, paths):
    for path in paths:
        response = client.post(API + "/extensions/install", json=json.loads(path.read_text()))
        assert response.status_code == 201, (path.name, response.text)


def build_templates(packages):
    templates = load(ROOT / "sources/templates.py", "templates").TEMPLATES
    with tempfile.TemporaryDirectory() as folder, workspace(folder) as client:
        install(client, packages)
        study = client.post(API + "/studies", json={"name": "Explore templates", "description": ""}).json()
        task = client.post(f"{API}/studies/{study['id']}/tasks", json={"name": "Templates", "description": ""}).json()
        for item in templates:
            draft = client.post(API + "/experiments", params={"task_id": task["id"]}, json=item["spec"],
                                headers={"Idempotency-Key": "build-" + item["id"]})
            assert draft.status_code == 201 and not draft.json()["field_errors"], (item["id"], draft.text)
            record = draft.json()
            version = client.post(f"{API}/experiments/{record['id']}/versions", json={"revision": record["revision"]})
            assert version.status_code == 201, (item["id"], version.text)
            exported = client.get(f"{API}/experiment-versions/{version.json()['id']}/template",
                                  params={"author": AUTHOR, "name": item["name"], "description": item["description"]})
            assert exported.status_code == 200, (item["id"], exported.text)
            out = ROOT / "templates" / f"{item['id']}.template.json"
            out.write_text(json.dumps(exported.json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(out.relative_to(ROOT))


if __name__ == "__main__":
    built = build_packages()
    if "--packages-only" not in sys.argv[1:]:
        build_templates(built)
