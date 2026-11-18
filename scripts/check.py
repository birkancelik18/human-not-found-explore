"""Check every package and study template in this repository, and optionally rebuild index.json.

    python3 scripts/check.py                # check only (pull requests)
    python3 scripts/check.py --write-index  # check, then write index.json (after a merge)

Needs Python 3.10+ and the `jsonschema` package.
"""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Draft202012Validator(json.loads((ROOT / "schemas/extension-manifest.schema.json").read_text()))
TEMPLATE = Draft202012Validator(json.loads((ROOT / "schemas/template.schema.json").read_text()))
FORMAT = "python.source.v1"


def schema_problems(validator, value):
    return [f"{'/'.join(map(str, error.path)) or '(root)'}: {error.message}" for error in validator.iter_errors(value)]


def added_at(path):
    """When the file was first committed, or now for a file not committed yet."""
    result = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "-1", "--", str(path)],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() or datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_package(path, data):
    problems = []
    if set(data) != {"manifest", "artifact"}:
        return ["A package needs exactly a manifest and an artifact."]
    manifest, artifact = data["manifest"], data["artifact"]
    problems += schema_problems(MANIFEST, manifest)
    if not isinstance(artifact, dict) or artifact.get("format") != FORMAT:
        problems.append(f"artifact.format must be {FORMAT}.")
    else:
        try:
            compile(artifact.get("source", ""), path.name, "exec")
        except SyntaxError as error:
            problems.append(f"Python syntax error on line {error.lineno}: {error.msg}")
    if not problems and path.name != f"{manifest['bundle_id']}-{manifest['version']}.hnf.json":
        problems.append(f"Name the file {manifest['bundle_id']}-{manifest['version']}.hnf.json.")
    return problems


def check_template(path, data, packages):
    problems = schema_problems(TEMPLATE, data)
    if problems:
        return problems
    for needed in data["packages"]:
        if (needed["bundle_id"], needed["version"]) not in packages:
            problems.append(f"Needs {needed['bundle_id']} {needed['version']}, which is not in packages/.")
    return problems


def main(write_index):
    problems, packages, templates = [], {}, []
    for path in sorted((ROOT / "packages").glob("*.hnf.json")):
        raw = path.read_bytes()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            problems.append(f"{path.relative_to(ROOT)}: invalid JSON ({error})")
            continue
        found = check_package(path, data)
        problems += [f"{path.relative_to(ROOT)}: {item}" for item in found]
        if not found:
            manifest = data["manifest"]
            packages[(manifest["bundle_id"], manifest["version"])] = {
                "path": str(path.relative_to(ROOT)), "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                "added_at": added_at(path), "manifest": manifest}
    for path in sorted((ROOT / "templates").glob("*.template.json")):
        raw = path.read_bytes()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            problems.append(f"{path.relative_to(ROOT)}: invalid JSON ({error})")
            continue
        found = check_template(path, data, packages)
        problems += [f"{path.relative_to(ROOT)}: {item}" for item in found]
        if not found:
            templates.append({"path": str(path.relative_to(ROOT)), "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                              "added_at": added_at(path), "id": path.name.removesuffix(".template.json"),
                              **{key: data[key] for key in ("name", "author", "description", "packages")}})
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"{len(packages)} packages and {len(templates)} templates passed the check.")
    if write_index:
        index = {"format": "hnf.explore-index.v1", "packages": list(packages.values()), "templates": templates}
        (ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main("--write-index" in sys.argv[1:]))
