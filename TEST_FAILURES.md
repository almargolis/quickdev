# Test Failures Guide

## Summary
- ✅ 34 tests passing
- ❌ 6 tests failing
- ⚠️ 0 tests with errors

## Detailed Breakdown

### 1. test_qdsqlite.py::test_create_db
**Status:** FAILED
**Error:** `AssertionError: assert...`
**Issue:** Schema assertion mismatch - expected schema differs from actual

**To fix:** Check if the database schema format has changed. Update the expected schema in the test.

---

### 2. test_httpautomation.py::test_simple_html_1
**Status:** FAILED
**Error:** `AttributeError: 'Crawler' object has no attribute 'FindNextText'`
**File:** `qdcore_tests/test_httpautomation.py`

**Issue:** Method name may have changed from `FindNextText` to `find_next_text` (Python convention)

**To fix:** Check if Crawler API was updated to use snake_case naming

---

### 3. test_qdhtml.py::test_basic
**Status:** FAILED
**Error:** `AttributeError: 'HtmlPage' object has no attribute 'body'`
**File:** `qdcore_tests/test_qdhtml.py:6`

**Code:**
```python
def test_basic():
    page = qdhtml.HtmlPage()
    paragraph = page.body.append(qdhtml.HtmlContent("p"))  # ← fails here
```

**Issue:** HtmlPage API changed - no longer has direct `.body` attribute

**To fix:** Update test to use correct HtmlPage API. Check if it's now `page.get_body()` or similar.

---

### 4. test_apache.py::test_config_vhosts
**Status:** FAILED
**Error:** `AttributeError: module 'qdutils_tests.test_qdstart' has no attribute 'MakeQdev'`
**File:** `qdutils_tests/test_apache.py:145`

**Code:**
```python
def test_config_vhosts(tmpdir):
    test_qdstart.MakeQdev(tmpdir)  # ← fails here
```

**Issue:** Helper function `MakeQdev` doesn't exist in test_qdstart

**To fix:** Check test_qdstart.py for the actual function name. Might be:
- `make_qdev()` (lowercase)
- `create_qdev()`
- Function was removed/renamed

---

### 5. test_hosting.py::test_init
**Status:** FAILED
**Error:** `AttributeError: module 'qdutils_tests.test_qdstart' has no attribute 'MakeQdev'`
**File:** `qdutils_tests/test_hosting.py:14`

**Same issue as #4** - needs MakeQdev function

---

### 6. test_hosting.py::test_site_register
**Status:** FAILED
**Error:** `AttributeError: module 'qdutils_tests.test_qdstart' has no attribute 'make_site'`
**File:** `qdutils_tests/test_hosting.py:18`

**Code:**
```python
def test_site_register(tmpdir):
    start = test_qdstart.make_site(tmpdir)  # ← fails here
```

**Issue:** Helper function `make_site` doesn't exist

**To fix:** Find correct function name in test_qdstart.py

---

### 7. test_xsynth.py::test_main
**Status:** FAILED
**Error:** `AttributeError: 'QdSite' object has no attribute 'reload'`
**File:** `qdcore/qdsite.py:44`

**Traceback:**
```python
def identify_site(site=None):
    if exenv.execution_env.execution_site is not None:
        if exenv.execution_env.execution_site.qdsite_valid:
            return exenv.execution_env.execution_site
        exenv.execution_env.execution_site.reload(qdsite_dpath=site)  # ← fails here
```

**Issue:** QdSite class no longer has `.reload()` method

**To fix:** Either:
- Add reload() method to QdSite class
- Update identify_site() to use new API
- Mock/skip this test if reload is no longer needed

---

## ✅ Fixed: qdimages tests

All 5 qdimages tests in `qdimages_tests/test_storage.py` are now **PASSING**:
- ✅ test_storage_initialization
- ✅ test_compute_hash
- ✅ test_hierarchical_path_generation
- ✅ test_save_image
- ✅ test_get_image_by_hash

**Fixed by:**
1. Added missing database models (ImageExif, SourceTracking) to models.py
2. Fixed Flask app context initialization in test fixtures
3. Aligned SQLAlchemy schema with raw SQLite expectations in storage.py
4. Implemented full test coverage for save and retrieval workflows

---

## Quick Commands

Run specific test:
```bash
pytest qdbase_tests/test_qdsqlite.py::test_create_db -v
```

Run all tests in a file:
```bash
pytest qdcore_tests/test_qdhtml.py -v
```

Run with detailed output:
```bash
pytest qdcore_tests/test_qdhtml.py::test_basic -vv --tb=long
```

Skip slow tests:
```bash
pytest -v -m "not slow"
```

---

## Files to Check

1. `qdutils_tests/test_qdstart.py` - Find actual helper function names
2. `qdcore/qdhtml.py` - Check HtmlPage API
3. `qdcore/qdsite.py` - Check QdSite API (reload method)
4. `qdcore/httpautomation.py` - Check Crawler method names

---

## Strategy

Recommended order to fix:

1. **Start with test helpers** (#4, #5, #6) - Fix MakeQdev/make_site references
2. **Fix API changes** (#3, #7) - Update HtmlPage.body and QdSite.reload
3. **Fix method names** (#2) - Update Crawler method calls
4. **Fix assertions** (#1) - Update expected database schema

Most of these are probably just naming updates or API changes you made intentionally. The tests just need to catch up!
