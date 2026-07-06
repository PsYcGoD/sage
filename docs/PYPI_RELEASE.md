# PyPI Release Prep

## What PyPI Is Used For

PyPI is the public Python package registry. Publishing SAGE there lets users install the CLI with:

```bash
pip install sage-cli
```

or, for isolated CLI installs:

```bash
pipx install sage-cli
```

The package name is `sage-cli`, but the command users run remains:

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

5. Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

6. Install from TestPyPI in a clean environment and run:

```bash
sage --version
sage gui
sage api status
```

7. Upload to PyPI:

```bash
python -m twine upload dist/*
```

## Not Done Yet

The actual PyPI upload requires a PyPI account/token. Do not mark PyPI release complete until the package is visible on PyPI and install-tested.
