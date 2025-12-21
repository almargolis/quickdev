# XSynth: Code Generation That Doesn't Suck

## The Problem with Code Generation

Most code generation tools fall into two camps:

**Camp 1: One-Time Scaffolding** (Rails, Django)
- Generate code once
- Modify the generated files
- Never regenerate (you'll lose your changes)
- Result: Stale boilerplate that diverges across projects

**Camp 2: Runtime Magic** (ORMs, meta-programming)
- No files to look at
- Debugging is a nightmare ("where is this method defined?")
- Performance overhead
- Result: "Magic" that breaks in subtle ways

**XSynth takes a different approach:** Preprocessor-based code generation that produces **readable, standard Python** you can inspect, debug, and understand.

## What is XSynth?

XSynth is a preprocessor that transforms `.xpy` (XSynth Python) files into standard `.py` files. It extends DRY (Don't Repeat Yourself) principles from **runtime** to **compile-time**.

**Runtime DRY**: Extract common code into functions
```python
def calculate_total(items):
    return sum(item.price for item in items)
```

**Compile-Time DRY**: Generate repetitive patterns from declarations
```python
#$define FIELDS name, price, quantity
# XSynth generates: __init__, to_dict(), from_dict(), etc.
```

## A Real Example: Data Models

### The Traditional Way

You're building an e-commerce app. You need models for Products, Orders, Customers.

**product.py** (100 lines)
```python
class Product:
    def __init__(self, name, price, quantity, category):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.category = category

    def to_dict(self):
        return {
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
        }

    @classmethod
    def from_dict(cls, data):
        required = ['name', 'price']
        for field in required:
            if field not in data:
                raise ValueError(f"Missing: {field}")

        return cls(
            name=data['name'],
            price=data['price'],
            quantity=data.get('quantity', 0),
            category=data.get('category'),
        )

    def validate(self):
        if not self.name:
            raise ValueError("Name required")
        if self.price < 0:
            raise ValueError("Price must be positive")
        # ...more validation
```

**order.py** (100 lines of similar code)
**customer.py** (100 lines of similar code)

**Total: 300+ lines** of nearly identical boilerplate.

### The XSynth Way

**product.xpy** (30 lines)
```python
#$define MODEL_NAME Product
#$define TABLE_NAME products
#$define FIELDS name, price, quantity, category
#$define REQUIRED_FIELDS name, price
#$define SEARCHABLE_FIELDS name, category

class $MODEL_NAME$:
    """$MODEL_NAME$ model - auto-generated methods."""

    __tablename__ = '$TABLE_NAME$'

    def __init__(self, $FIELDS$):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.category = category

    def to_dict(self):
        return {
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
        }

    @classmethod
    def from_dict(cls, data):
        required = ['name', 'price']  # From REQUIRED_FIELDS
        for field in required:
            if field not in data:
                raise ValueError(f"Missing: {field}")

        return cls(
            name=data['name'],
            price=data['price'],
            quantity=data.get('quantity', 0),
            category=data.get('category'),
        )
```

Run XSynth:
```bash
python qdutils/xsynth.py product.xpy
```

Get **product.py** with all substitutions applied.

**Change fields?** Update the `#$define` and regenerate. All methods stay in sync.

## How XSynth Works

### 1. Define Substitutions

```python
#$define NAME Product
#$define FIELDS id, name, price
```

### 2. Use Substitutions

```python
class $NAME$:
    def __init__(self, $FIELDS$):
        pass
```

### 3. Generate Python

```python
class Product:
    def __init__(self, id, name, price):
        pass
```

## XSynth Syntax

### Basic Substitution

```python
#$define GREETING Hello

print("$GREETING$ World")  # → print("Hello World")
```

### Quoted Substitution

```python
#$define API_KEY abc123

headers = {"Authorization": $"API_KEY$"}
# → headers = {"Authorization": "abc123"}
```

### Module References

```python
# In constants.xpy
#$define VERSION 1.0.0

# In app.xpy
print($"constants.VERSION$)
# → print("1.0.0")
```

## Real-World Use Cases

### 1. Data Models with Many Fields

**Problem**: Product model with 20 fields. Writing `to_dict()`, `from_dict()`, `__eq__()`, etc. is tedious and error-prone.

**XSynth Solution**:
```python
#$define FIELDS id, name, description, price, quantity, sku, barcode, category, subcategory, brand, weight, dimensions, color, size, material, origin, warranty, rating, reviews_count, created_at

class Product:
    def __init__(self, $FIELDS$):
        # XSynth expands to all 20 parameters
        self.id = id
        self.name = name
        # ... all 20 fields

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            # ... all 20 fields
        }
```

Add a field? Change one line, regenerate.

### 2. API Clients with Consistent Patterns

**Problem**: REST API with 50 endpoints. Each needs the same error handling, retries, logging.

**XSynth Solution**:
```python
#$define ENDPOINTS users, products, orders, customers, invoices

# Generate methods for each endpoint
def get_$ENDPOINTS$(self, id):
    return self._request('GET', '/$ENDPOINTS$/{id}')

def list_$ENDPOINTS$(self, **filters):
    return self._request('GET', '/$ENDPOINTS$', params=filters)

def create_$ENDPOINTS$(self, data):
    return self._request('POST', '/$ENDPOINTS$', json=data)
```

### 3. Configuration Management

**Problem**: Different configs for dev, staging, production. Want to ensure consistency.

**XSynth Solution**:
```python
# config_base.xpy
#$define ENV production

DATABASE_URL = $"config.$ENV$.DB_URL$
API_KEY = $"config.$ENV$.API_KEY$
DEBUG = $config.$ENV$.DEBUG$
```

### 4. SQL Generation

**Problem**: Writing SQL for 20 tables is repetitive.

**XSynth Solution**:
```python
#$define TABLE products
#$define COLUMNS id, name, price, quantity

CREATE TABLE $TABLE$ (
    $COLUMNS$  -- Expands to column definitions
);

INSERT INTO $TABLE$ ($COLUMNS$) VALUES (?, ?, ?, ?);

SELECT $COLUMNS$ FROM $TABLE$ WHERE id = ?;
```

## When to Use XSynth

✓ **Data models** with many fields
✓ **CRUD operations** that follow patterns
✓ **API clients** with consistent endpoints
✓ **SQL queries** for multiple tables
✓ **Configuration files** across environments
✓ **Test fixtures** with repeated setup

✗ **Complex business logic** (use regular Python)
✗ **One-off code** (not worth the overhead)
✗ **Simple apps** (may be overkill)

## XSynth vs. Alternatives

### vs. Jinja2 Templates

**Jinja2**: Template engine for generating any text
```jinja2
{% for field in fields %}
    self.{{ field }} = {{ field }}
{% endfor %}
```

**XSynth**: Simpler syntax for Python-specific patterns
```python
#$define FIELDS name, email
self.$FIELDS$ = $FIELDS$  # More readable for Python
```

**When to use Jinja2**: Complex logic, conditionals, loops
**When to use XSynth**: Simple substitutions in Python files

### vs. Python Metaclasses

**Metaclasses**: Runtime magic
```python
class User(ModelMeta):
    fields = ['name', 'email']
# Where is __init__ defined? ¯\_(ツ)_/¯
```

**XSynth**: Generated code you can read
```python
# Generated product.py
class User:
    def __init__(self, name, email):  # Right here!
        self.name = name
        self.email = email
```

**When to use metaclasses**: Dynamic behavior at runtime
**When to use XSynth**: Generate code once, run normally

### vs. Dataclasses

**Dataclasses**: Great for simple cases
```python
@dataclass
class User:
    name: str
    email: str
```

**XSynth**: More control over generation
```python
#$define FIELDS name, email
#$define SEARCHABLE name, email

# Generate custom to_dict(), from_dict(), search(), etc.
```

**When to use dataclasses**: Standard Python data structures
**When to use XSynth**: Custom patterns beyond dataclass capabilities

## Advanced Features

### Dict Declarations

```python
#$ dict Product {
    field name string required
    field price float required
    field quantity int default=0
}
```

Generates: Model class, to_dict(), from_dict(), validate(), SQL schema

### Action Declarations

```python
#$ action CreateProduct {
    input ProductData
    output Product
    validate required_fields
    execute create_in_db
}
```

Generates: Route handler, validation, error handling, logging

### Template Includes

```python
#$include common/error_handling.xpy
#$include common/logging.xpy
```

Share patterns across files.

## Workflow

### 1. Develop in .xpy

```python
# user.xpy
#$define FIELDS name, email, role

class User:
    def __init__(self, $FIELDS$):
        self.name = name
        self.email = email
        self.role = role
```

### 2. Generate .py

```bash
python qdutils/xsynth.py user.xpy
```

### 3. Import and Use

```python
from models.user import User  # Uses generated user.py

user = User(name="Alice", email="alice@example.com", role="admin")
```

### 4. Modify and Regenerate

Add a field:
```python
#$define FIELDS name, email, role, created_at
```

Regenerate:
```bash
python qdutils/xsynth.py user.xpy
```

All methods automatically updated.

## Best Practices

### 1. Edit .xpy, Not .py

Add a header to generated files:
```python
# AUTO-GENERATED by XSynth from user.xpy
# DO NOT EDIT - Edit the .xpy file instead
```

### 2. Version Control Both

Commit both .xpy (source) and .py (generated) files:
- .xpy shows the pattern
- .py shows the actual code (reviewable)

### 3. Use for Patterns, Not Logic

**Good**:
```python
#$define FIELDS name, email
# Generate __init__, to_dict(), from_dict()
```

**Bad**:
```python
#$define BUSINESS_LOGIC calculate_discount_based_on_user_tier
# Too complex, use regular Python
```

### 4. Keep Substitutions Simple

**Good**:
```python
#$define MODEL_NAME Product
#$define FIELDS id, name, price
```

**Bad**:
```python
#$define COMPLEX_CALC ((price * quantity * tax_rate) + shipping) - discount
# Just write Python
```

## Debugging

### See What Gets Generated

```bash
# Generate and compare
python qdutils/xsynth.py user.xpy
diff user.xpy user.py
```

### Trace Substitutions

```bash
# Run with verbose mode
python qdutils/xsynth.py --verbose user.xpy
```

### Check the .py File

The generated file is readable Python - inspect it!

## Real-World Example

Here's a production example from a SaaS application:

**Before XSynth: 5 model files, 500 lines total**
- product.py (100 lines)
- customer.py (100 lines)
- order.py (100 lines)
- invoice.py (100 lines)
- payment.py (100 lines)

Each had the same patterns:
- `__init__` with all fields
- `to_dict()` serialization
- `from_dict()` deserialization
- `validate()` validation
- `search()` search logic

**After XSynth: 5 .xpy files, 150 lines total**
```python
#$define MODEL_NAME Product
#$define FIELDS id, name, price, quantity
#$define REQUIRED name, price
#$define SEARCHABLE name

# 30 lines of pattern definition
# Generates 100 lines of Python
```

**Savings: 70% fewer lines to maintain**

**Benefits**:
- Change validation logic once, regenerate all models
- Add a new model in 30 lines
- Consistency across all models guaranteed
- Less to test (the pattern is tested once)

## Getting Started

### 1. Install QuickDev

```bash
git clone https://github.com/quickdev/quickdev
cd quickdev
```

### 2. Try the Tutorial

```bash
cd examples/xsynth-tutorial
python ../../qdutils/xsynth.py user_model.xpy
# Compare user_model.xpy and generated user_model.py
```

### 3. Create Your First .xpy

```python
# mymodel.xpy
#$define MODEL_NAME MyModel
#$define FIELDS id, name, value

class $MODEL_NAME$:
    def __init__(self, $FIELDS$):
        self.id = id
        self.name = name
        self.value = value
```

### 4. Generate

```bash
python path/to/xsynth.py mymodel.xpy
```

### 5. Marvel

Check out `mymodel.py` - readable, standard Python!

## The Philosophy

XSynth embodies a simple idea: **Generate code, don't hide it.**

- **Not runtime magic**: No metaclasses, no __getattr__ hacks
- **Not one-time scaffolding**: Regenerate whenever you want
- **Just a preprocessor**: .xpy → .py, that's it

The generated code is:
- ✓ Readable
- ✓ Debuggable
- ✓ Standard Python
- ✓ Version-controllable
- ✓ Inspectable

It's compile-time DRY for developers who like to know what's happening.

## Learn More

- **Examples**: https://github.com/quickdev/quickdev/tree/master/examples/xsynth-tutorial
- **Documentation**: https://quickdev.readthedocs.io/xsynth
- **Source**: https://github.com/quickdev/quickdev/blob/master/qdutils/xsynth.py

## Conclusion

Code generation doesn't have to suck. It doesn't have to be:
- Magic you can't understand
- One-time scaffolding that gets stale
- Complex template languages

XSynth is simple:
1. Define patterns in .xpy
2. Generate Python with xsynth.py
3. Use the generated code normally

It's DRY taken to its logical conclusion: **Define it once, generate it everywhere.**

---

*Ready to try XSynth? [Check out the examples →](https://github.com/quickdev/quickdev/tree/master/examples/xsynth-tutorial)*
