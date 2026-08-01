# PyPI Release Prep

## What PyPI Is Used For

PyPI is the public Python package registry. Publishing SAGE there lets users install the CLI with:

```bash
pip install psycgod-sage
```

or, for isolated CLI installs:

```bash
pipx install psycgod-sage
```

The package name is `psycgod-sage`, but the command users run remains:

```bash
sage
```

## Why This Matters Before 100 Users

- Users can install SAGE without cloning GitHub.
- Agents and developers can reproduce the same install command.
- README, release notes, and demos can point to one simple public install path.
- It gives early users a normal Python CLI install experience.

## Release Steps

1. Verify metadata:

```bash
python -m pytest tests/test_public_package_metadata.py -q
```

2. Run tests:

```bash
python -m pytest -q
```

3. Build distributions:

```bash
python -m build
```

4. Inspect package contents:

```bash
python -m twine check dist/*
```

5. Publish from GitHub using trusted publishing for both registries:

- Create a PyPI pending publisher for project `psycgod-sage`.
- Use repository `PsYcGoD/sage`.
- Use workflow `pypi-publish.yml`.
- Use environment `pypi`.
- Configure npm trusted publishing for `PsYcGoD/sage`, workflow `pypi-publish.yml`, environment `npm`, with `npm publish` allowed.
- Publish a GitHub release. The workflow uploads PyPI first, waits until that exact core version is visible, and then publishes the thin npm launcher using OIDC.

No PyPI API token is needed when Trusted Publishing is configured correctly.

6. After the GitHub release workflow succeeds, install both entry points in clean environments and run:

```bash
pip install psycgod-sage
sage --version
sage api status
npx -y psycgod-sage@latest --version
```

## Not Done Yet

Do not mark PyPI release complete until the package is visible on PyPI and install-tested with `pip install psycgod-sage`.

Registry configuration is case-sensitive. Both trusted publishers must use `PsYcGoD/sage` and the exact workflow filename `pypi-publish.yml`; the environments are `pypi` and `npm` respectively.
