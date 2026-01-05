# GitHub Migration Guide

This guide will help you move QuickDev from GitLab to GitHub and publish to PyPI.

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository:
   - **Name:** `quickdev`
   - **Description:** "Metaprogramming toolkit for Python - eliminates boilerplate through code generation"
   - **Visibility:** Public
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

## Step 2: Update Git Remote

```bash
# Remove old GitLab remote
git remote remove origin

# Add new GitHub remote
git remote add origin git@github.com:almargolis/quickdev.git

# Verify
git remote -v
```

## Step 3: Push to GitHub

```bash
# Push all branches and tags
git push -u origin master
git push --tags

# Or if you want to push all branches
git push -u origin --all
git push --tags
```

## Step 4: Set Up PyPI

### 4.1 Create PyPI Account (if needed)

1. Go to https://pypi.org/account/register/
2. Create account and verify email

### 4.2 Create API Tokens

1. Go to https://pypi.org/manage/account/
2. Scroll to "API tokens"
3. Click "Add API token"
   - **Token name:** `quickdev-publishing`
   - **Scope:** Select "Entire account" (or specific projects after first publish)
4. **IMPORTANT:** Copy the token immediately (starts with `pypi-AgE...`)
5. Repeat for TestPyPI at https://test.pypi.org/

### 4.3 Configure Credentials

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgE...YOUR_TOKEN_HERE...

[testpypi]
username = __token__
password = pypi-AgE...YOUR_TESTPYPI_TOKEN_HERE...
```

**Important:** Keep these tokens secret! Add `~/.pypirc` to your global `.gitignore`.

## Step 5: Test Publish to TestPyPI

```bash
# Activate virtual environment
source ezdev.venv/bin/activate

# Install publishing tools
pip install build twine

# Test publish qdbase
./scripts/publish-package.sh qdbase --test

# Verify on TestPyPI
# Visit: https://test.pypi.org/project/qdbase/

# Test installation
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ qdbase

# Test publish xsynth
./scripts/publish-package.sh xsynth --test
```

## Step 6: Publish to Production PyPI

Once you've verified on TestPyPI:

```bash
# Publish qdbase
./scripts/publish-package.sh qdbase --prod

# Verify on PyPI
# Visit: https://pypi.org/project/qdbase/

# Publish xsynth
./scripts/publish-package.sh xsynth --prod

# Visit: https://pypi.org/project/xsynth/
```

## Step 7: Tag the Release

```bash
# Tag the initial release
git tag qdbase-v0.2.0
git tag xsynth-v0.3.0

# Push tags to GitHub
git push --tags
```

## Step 8: Set Up GitHub Secrets (Optional)

For automated publishing via GitHub Actions:

1. Go to your GitHub repo
2. Settings → Secrets and variables → Actions
3. Add repository secrets:
   - `PYPI_API_TOKEN` - Your PyPI token
   - `TEST_PYPI_API_TOKEN` - Your TestPyPI token

Now you can publish from GitHub Actions UI!

## Step 9: Update Package Status

After publishing, update the badges in README.md:

```markdown
# QuickDev

[![PyPI - qdbase](https://img.shields.io/pypi/v/qdbase)](https://pypi.org/project/qdbase/)
[![PyPI - xsynth](https://img.shields.io/pypi/v/xsynth)](https://pypi.org/project/xsynth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

## Troubleshooting

### "Repository already exists"
Someone else has claimed the package name. Choose a different name or contact PyPI support.

### "Invalid or non-existent authentication"
Check your `~/.pypirc` file has the correct token.

### "File already exists"
You've already published this version. Bump the version number:
```bash
python scripts/bump-version.py qdbase patch
```

### Permission denied on git push
Make sure you've set up SSH keys with GitHub:
```bash
ssh -T git@github.com
# Should say: "Hi username! You've successfully authenticated"
```

## Quick Command Summary

```bash
# Complete migration in one go:

# 1. Update remote
git remote remove origin
git remote add origin git@github.com:almargolis/quickdev.git

# 2. Push to GitHub
git push -u origin master
git push --tags

# 3. Test publish
./scripts/publish-package.sh qdbase --test
./scripts/publish-package.sh xsynth --test

# 4. Production publish
./scripts/publish-package.sh qdbase --prod
./scripts/publish-package.sh xsynth --prod

# 5. Tag releases
git tag qdbase-v0.2.0
git tag xsynth-v0.3.0
git push --tags
```

## Post-Migration Checklist

- [ ] GitHub repository created
- [ ] Code pushed to GitHub
- [ ] PyPI account created
- [ ] TestPyPI tokens configured
- [ ] qdbase published to PyPI
- [ ] xsynth published to PyPI
- [ ] Releases tagged in git
- [ ] README badges updated (optional)
- [ ] GitHub Secrets configured for Actions (optional)

## Next Steps

After successful migration:

1. **Update trellis-cms** to use published packages
2. **Publish qdflask and qdimages** (already have setup.py)
3. **Share on social media** - you've just open sourced 3 decades of work!
4. **Write blog post** about the journey from C library to Python toolkit

---

**Need help?** Check the [scripts/README.md](scripts/README.md) for detailed publishing instructions.
