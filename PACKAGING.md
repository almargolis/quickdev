# QuickDev Package Architecture

This document describes the multi-package structure and publishing strategy for QuickDev.

## Package Strategy: Monorepo with À La Carte Consumption

QuickDev uses a **monorepo** for development but publishes **separate packages** to PyPI, allowing users to install only what they need.

## Package Tiers

### Tier 1: Foundation
**qdbase** - Pure Python utilities (zero external deps)
- Published: `pip install qdbase`
- Location: `./qdbase/`
- Dependencies: None (stdlib only)
- Use cases: Anyone can use these utilities standalone

### Tier 2: Metaprogramming
**xsynth** - Preprocessor for generating Python from .xpy files
- Published: `pip install xsynth`
- Location: `./xsynth/` (wrapper) + `./qdutils/xsynth.py` (implementation)
- Dependencies: `qdbase>=0.2.0`
- Use cases: Projects using XSynth preprocessing

### Tier 3: Flask Extensions (Independent)
These packages have **NO dependencies** on qdbase/xsynth:

**qdflask** - Flask authentication
- Published: `pip install qdflask`
- Location: `./qdflask/`
- Dependencies: Flask, Flask-Login, Flask-SQLAlchemy, Flask-Mail
- Use cases: Any Flask app needing auth

**qdimages** - Flask image management
- Published: `pip install qdimages`
- Location: `./qdimages/`
- Dependencies: Flask, Pillow, xxhash, rembg
- Use cases: Any Flask app needing image handling

**qdcomments** - Flask commenting system
- Published: `pip install qdcomments`
- Location: `./qdcomments/`
- Dependencies: Flask, Flask-SQLAlchemy
- Use cases: Any Flask app needing comments

### Tier 4: Applications
**trellis-cms** - Digital garden CMS
- Published: `pip install trellis-cms`
- Location: Separate repo (future)
- Dependencies: qdflask, qdimages, qdcomments

## Dependency Graph

```
┌─────────┐
│ qdbase  │  (stdlib only)
└────┬────┘
     │
     ├─────────┐
     │         │
┌────▼────┐  ┌─▼───────┐
│ xsynth  │  │ qdcore  │  (optional, internal use)
└─────────┘  └─────────┘

┌──────────┐  ┌───────────┐  ┌────────────┐
│ qdflask  │  │ qdimages  │  │ qdcomments │  (independent)
└─────┬────┘  └─────┬─────┘  └──────┬─────┘
      │             │                │
      └─────────────┴────────────────┘
                    │
              ┌─────▼──────┐
              │ trellis-cms│
              └────────────┘
```

## Published vs. Internal Packages

### Published to PyPI
- ✅ qdbase - Foundation utilities
- ✅ xsynth - Preprocessor
- ✅ qdflask - Flask auth
- ✅ qdimages - Flask images
- ✅ qdcomments - Flask comments
- ✅ trellis-cms - CMS application

### Internal (Not Published)
- ⊘ qdcore - Contains legacy dependencies (ezcore, pylib)
- ⊘ qdutils - Development utilities
- ⊘ qdconfig - Configuration helpers

**Future:** Clean up qdcore to remove legacy deps, then publish as "qdcore" with useful utilities like qdhtml, httpautomation, datastore.

## Development Workflow

### Working in the Monorepo

```bash
# Install all packages in development mode
pip install -e ./qdbase
pip install -e ./xsynth
pip install -e ./qdflask
pip install -e ./qdimages
pip install -e ./qdcomments

# Or use the development setup script
./scripts/dev-setup.sh  # TODO: Create this
```

### Publishing a Package

```bash
# 1. Bump version
python scripts/bump-version.py qdbase patch

# 2. Test build
./scripts/build-all.sh

# 3. Publish to TestPyPI
./scripts/publish-package.sh qdbase --test

# 4. Test installation
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ qdbase

# 5. Publish to PyPI
./scripts/publish-package.sh qdbase --prod

# 6. Tag release
git tag qdbase-v0.2.1
git push --tags
```

## User Consumption Patterns

### Pattern 1: Just Flask Auth
```bash
pip install qdflask
```
```python
from qdflask import init_auth, create_admin_user
```

### Pattern 2: Complete Flask Stack
```bash
pip install qdflask qdimages qdcomments
```

### Pattern 3: QuickDev Metaprogramming
```bash
pip install qdbase xsynth
```
```bash
xsynth  # Process .xpy files
```

### Pattern 4: Full QuickDev (for your projects)
```bash
git clone https://github.com/yourusername/quickdev
pip install -e ./qdbase
pip install -e ./xsynth
# etc.
```

## Migration from Existing PyPI Packages

You already have these on PyPI:
- `quickdev` (Aug 14, 2021) - Version 0.1.x
- `qdbase` (Sep 5, 2021) - Version 0.1.x
- `xsynth` (Sep 5, 2021) - Version 0.1.x
- `xsource` (Sep 4, 2021) - Created but never released
- `trellis-cms` (Nov 26, 2025) - Active

**Recommended approach:**
1. **Bump to 0.2.0+** for new releases (qdbase, xsynth)
2. **Deprecate old `quickdev` package** - Add notice pointing to specific packages
3. **Keep `xsource` as-is** - It's now part of qdbase
4. **Continue trellis-cms** - Already following good patterns

## Files Created

```
.
├── qdbase/
│   ├── setup.py              ✓ NEW
│   └── README.md             ✓ NEW
├── xsynth/
│   ├── setup.py              ✓ NEW
│   ├── __init__.py           ✓ NEW
│   └── README.md             ✓ NEW
├── qdflask/
│   ├── setup.py              ✓ EXISTS
│   └── README.md             ✓ EXISTS
├── qdimages/
│   ├── setup.py              ✓ EXISTS
│   └── README.md             ✓ EXISTS
├── scripts/
│   ├── build-all.sh          ✓ NEW
│   ├── publish-package.sh    ✓ NEW
│   ├── bump-version.py       ✓ NEW
│   └── README.md             ✓ NEW
├── .github/workflows/
│   ├── test-packages.yml     ✓ NEW
│   └── publish-package.yml   ✓ NEW
└── PACKAGING.md              ✓ NEW (this file)
```

## Next Steps

1. **Test the build system:**
   ```bash
   ./scripts/build-all.sh
   ```

2. **Create GitHub secrets** for automated publishing:
   - `PYPI_API_TOKEN`
   - `TEST_PYPI_API_TOKEN`

3. **Publish qdbase and xsynth** to PyPI (new versions)

4. **Update trellis-cms** to use published packages instead of local paths

5. **Consider cleaning up qdcore** to make it publishable

6. **Extract reusable parts** from other projects (he_logo, my_trig.py)

## Questions to Consider

1. **Licensing:** All files show "MIT License" - confirm this is correct
2. **Author email:** Using "albert@quickdev.org" - is this active?
3. **Repository URL:** Using github.com/almargolis/quickdev - is this public?
4. **qdcore:** Worth cleaning up and publishing, or keep internal?
5. **Version numbers:** Start fresh at 1.0.0 or continue from 0.2.0?
