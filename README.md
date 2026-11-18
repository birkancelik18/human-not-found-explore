# Human Not Found Explore

The packages and study templates listed in **Explore** in Human Not Found.
The app reads `index.json` from this repository and downloads files from it
when a researcher installs a package or uses a template.

- **Packages** (`packages/`): component packages, `.hnf.json` files made with
  the Python SDK. A package holds one or more components: activities,
  procedures, participant behaviours and measures.
- **Study templates** (`templates/`): ready-to-run study designs, exported from
  a published configuration with **Export as template**. A template lists the
  packages it needs.

## Publish

1. Fork this repository.
2. Add your file:
   - a package as `packages/<bundle_id>-<version>.hnf.json`;
   - a template as `templates/<short-name>.template.json`, with every package it
     needs already in `packages/`.
3. Open a pull request. The check runs automatically.

A new version of a package is a new file; never edit a published one,
because experiments pin the exact version they ran with.

## Review

Components run Python on the researcher's computer, with their access. Every
pull request is reviewed by the maintainer before it is merged, and nothing
appears in Explore until it is merged. Reviews look at:

- what the code does, and whether its permissions match;
- the `about` text: it should say plainly what each component does;
- for templates, that the design matches the study it claims to replicate.

## Sources and rebuilding

The first-party packages and templates are built from `sources/`:

- `sources/<bundle_id>/component.py` and `manifest.json`: the Python source and manifest of each package;
- `sources/templates.py`: the study design of each template.

`scripts/build.py` packs every source into `packages/` with the app's SDK and regenerates `templates/` through the
app's own **Export as template** endpoint (in a temporary workspace), so template checksums match the packages.
`scripts/verify.py` installs everything in a fresh temporary workspace, uses each template and runs a pilot of every
condition with the free test model, checking that each run completes with every measure ok. Both need a local
checkout of the Human Not Found app; run them with its Python environment, and set `HNF_APP` to its folder if it is
not at `../AUI-Team-Simulator/implementation/human-not-found-v2`.

```sh
$HNF_APP/.venv/bin/python scripts/build.py
$HNF_APP/.venv/bin/python scripts/verify.py
```

Change a package's version when you change its source or manifest.

## Check locally

```sh
pip install jsonschema
python3 scripts/check.py
```

`index.json` is rebuilt automatically after each merge. Do not edit it by hand.
