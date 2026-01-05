# QuickDev Monorepo Publishing Scripts

This directory contains scripts for managing and publishing multiple Python packages from the QuickDev monorepo.

## Scripts Overview

### 1. `build-all.sh`
Builds distribution packages for all QuickDev packages without publishing.

```bash
./scripts/build-all.sh
```

Creates wheel and source distributions in each package's `dist/` directory. Useful for testing before release.

### 2. `publish-package.sh`
Publishes a single package to PyPI or TestPyPI.

```bash
# Publish to TestPyPI (default, for testing)
./scripts/publish-package.sh qdbase --test

# Publish to production PyPI
./scripts/publish-package.sh qdbase --prod
```

**Available packages:**
- `qdbase` - Foundation utilities
- `xsynth` - Preprocessor
- `qdflask` - Flask authentication
- `qdimages` - Flask image management
- `qdcomments` - Flask commenting system

### 3. `bump-version.py`
Increments version numbers following semantic versioning.

```bash
# Bump patch version (0.2.0 -> 0.2.1)
python scripts/bump-version.py qdbase patch

# Bump minor version (0.2.1 -> 0.3.0)
python scripts/bump-version.py qdflask minor

# Bump major version (0.3.0 -> 1.0.0)
python scripts/bump-version.py xsynth major

# Bump all packages at once
python scripts/bump-version.py all patch
```

Automatically updates version in:
- `setup.py` (required)
- `__init__.py` (if `__version__` exists)

## Publishing Workflow

### Initial Setup

1. **Install publishing tools:**
   ```bash
   pip install build twine
   ```

2. **Configure PyPI credentials:**
   ```bash
   # Create ~/.pypirc with your API tokens
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-AgE...  # Your PyPI API token

   [testpypi]
   username = __token__
   password = pypi-AgE...  # Your TestPyPI API token
   ```

### Publishing a Package

1. **Bump the version:**
   ```bash
   python scripts/bump-version.py qdbase patch
   ```

2. **Test the build:**
   ```bash
   ./scripts/build-all.sh
   ```

3. **Publish to TestPyPI first:**
   ```bash
   ./scripts/publish-package.sh qdbase --test
   ```

4. **Test installation from TestPyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ qdbase
   ```

5. **If all looks good, publish to production PyPI:**
   ```bash
   ./scripts/publish-package.sh qdbase --prod
   ```

6. **Commit and tag:**
   ```bash
   git add qdbase/setup.py qdbase/__init__.py
   git commit -m "Bump qdbase to v0.2.1"
   git tag qdbase-v0.2.1
   git push && git push --tags
   ```

## GitHub Actions Automation

### Automated Testing
The `.github/workflows/test-packages.yml` workflow runs automatically on:
- Push to main/master/develop branches
- Pull requests

Tests all packages across Python 3.8-3.12.

### Manual Publishing
The `.github/workflows/publish-package.yml` workflow can be triggered manually:

1. Go to Actions tab in GitHub
2. Select "Publish Package to PyPI"
3. Click "Run workflow"
4. Choose package and environment (testpypi/pypi)

**Required GitHub Secrets:**
- `TEST_PYPI_API_TOKEN` - TestPyPI API token
- `PYPI_API_TOKEN` - Production PyPI API token

## Package Structure

Each publishable package has:
```
package_name/
├── setup.py          # Package metadata and dependencies
├── README.md         # Package documentation
├── __init__.py       # Package initialization (optional __version__)
└── ...              # Package source files
```

## Dependencies Between Packages

```
qdbase (no deps)
  └─ xsynth (requires qdbase)

qdflask (no QuickDev deps)
qdimages (no QuickDev deps)
qdcomments (no QuickDev deps)
```

## Tips

- **Always test on TestPyPI first** - You can't delete releases from PyPI
- **Use semantic versioning** - MAJOR.MINOR.PATCH
- **Update CHANGELOG.md** - Document changes in each release
- **Tag releases in git** - Makes it easy to track what was published
- **Build locally first** - Catch issues before publishing

## Troubleshooting

**Build fails:**
```bash
# Clean old builds
rm -rf package_name/build package_name/dist package_name/*.egg-info
```

**Version already exists on PyPI:**
- Bump version and try again
- You cannot overwrite existing versions on PyPI

**Import errors after publishing:**
- Check that dependencies are listed in `install_requires`
- Verify package structure with `pip install -e ./package_name`

**TestPyPI installation fails:**
- TestPyPI doesn't have all dependencies
- Use: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ package_name`
