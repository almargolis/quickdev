# QuickDev Examples

These examples demonstrate QuickDev's core value proposition: **eliminating boilerplate through idioms and code generation**.

## Quick Start Guide

### 1. **Before/After Comparison** ⭐ START HERE
**Path:** `before-after/`

See the dramatic difference between traditional Flask development and QuickDev idioms.

- `before_manual.py` - 200+ lines of auth boilerplate
- `after_quickdev.py` - Same functionality in 30 lines

**Why start here:** Immediately understand the value proposition

```bash
cd before-after
python before_manual.py  # Traditional approach
python after_quickdev.py # QuickDev approach
```

### 2. **Flask Integration**
**Path:** `flask-integration/`

Learn how to add QuickDev idioms to any Flask application.

- Complete auth system with `init_auth(app, db)`
- Image management with `init_image_manager(app, db)`
- Shows real integration patterns

**Key lesson:** QuickDev complements Flask, doesn't replace it

```bash
cd flask-integration
pip install -e ../../qdflask
pip install -e ../../qdimages
python app.py
```

### 3. **XSynth Preprocessor Tutorial**
**Path:** `xsynth-tutorial/`

Understand how XSynth generates Python code from `.xpy` files.

- `user_model.xpy` - Source with XSynth directives
- `user_model.py` - Generated Python output
- Learn `#$define` and `$substitution$` syntax

**Key lesson:** Code generation extends DRY principles

```bash
cd xsynth-tutorial
python ../../qdutils/xsynth.py .
# Compare user_model.xpy vs user_model.py
```

## Examples Overview

| Example | What It Shows | Lines Saved | Best For |
|---------|---------------|-------------|----------|
| **before-after** | Same app, traditional vs QuickDev | 85%+ | Understanding value |
| **flask-integration** | Real integration with Flask | N/A | Getting started |
| **xsynth-tutorial** | Code generation mechanics | Varies | Advanced usage |

## QuickDev Philosophy

These examples demonstrate three core concepts:

### 1. Idioms, Not Framework

QuickDev is a **collection of patterns**, not a competing framework:

```python
# You still use Flask
from flask import Flask, render_template
app = Flask(__name__)

# QuickDev adds idioms
from qdflask import init_auth
init_auth(app, db)  # Auth idiom

# Write your app-specific code
@app.route('/products')
def list_products():
    # Your logic here
```

### 2. Code Generation, Not Runtime Magic

XSynth generates **readable Python** at preprocessing time:

```python
# You write (.xpy)
#$define FIELDS username, email
class User:
    def __init__(self, $FIELDS$):
        pass

# XSynth generates (.py)
class User:
    def __init__(self, username, email):
        pass
```

No runtime overhead, no magic imports, just Python.

### 3. Use What You Need

QuickDev is modular - pick the idioms you want:

- ✓ Use qdflask for auth, skip everything else
- ✓ Use XSynth for data models, write routes manually
- ✓ Use qdimages standalone in Django
- ✓ Create your own idioms following the same patterns

## Learning Path

**Beginner:**
1. Run before/after examples
2. Read the README files
3. Understand the value proposition

**Intermediate:**
1. Integrate qdflask into a Flask project
2. Experiment with XSynth substitutions
3. Read qdflask/qdimages source code

**Advanced:**
1. Create custom idioms for your patterns
2. Use XSynth `#$ dict` and `#$ action` declarations
3. Build your own reusable packages

## Common Questions

### "Is this like Rails scaffolding?"

Partially, but better:
- Rails scaffolding = one-time generation
- QuickDev idioms = maintained packages you import

Update qdflask → all your projects get the fix.

### "What if I need to customize?"

Three options:
1. **Configure** - Most idioms accept options
2. **Subclass** - Extend generated code
3. **Fork** - Copy and modify for your needs

### "Does it work with Django/FastAPI?"

The **idioms approach** works anywhere:
- qdflask/qdimages are Flask-specific
- XSynth works with any Python
- Create idioms for YOUR framework

### "Is the generated code readable?"

Yes! Check `xsynth-tutorial/user_model.py` - it's standard Python.

### "How mature is this?"

QuickDev has been in development since the 1990s, evolved through decades of real-world use. Currently being prepared for open source release.

## Next Steps

After exploring these examples:

1. **Read the main README** (`../README.md`) for project overview
2. **Check qdflask/qdimages READMEs** for detailed package docs
3. **Browse qdcore/*.xpy files** for advanced XSynth patterns
4. **Consider your own idioms** - What do YOU rewrite constantly?

## Contributing Examples

Have an idiom worth sharing? Ideas for examples:

- CRUD API with SQLAlchemy
- CSV import/export patterns
- Email sending patterns
- Background job patterns
- API client patterns

QuickDev is about capturing YOUR patterns as reusable code.

## Feedback

These examples are part of the open source preparation. If anything is unclear or you'd like to see additional examples, please open an issue at:
https://github.com/anthropics/claude-code/issues

---

**Remember:** QuickDev isn't about learning a new framework. It's about **not rewriting the same code** over and over.
