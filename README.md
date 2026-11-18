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

## Check locally

```sh
pip install jsonschema
python3 scripts/check.py
```

`index.json` is rebuilt automatically after each merge. Do not edit it by hand.
