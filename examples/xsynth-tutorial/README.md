# XSynth Tutorial: Code Generation with Preprocessor

XSynth is QuickDev's preprocessor that transforms `.xpy` files into standard Python `.py` files, eliminating repetitive code through template substitution.

## The Problem XSynth Solves

When building data models, you often repeat field names in multiple places:

```python
class User:
    def __init__(self, username, email, created_at, last_login):
        self.username = username      # Repetition 1
        self.email = email            # Repetition 2
        self.created_at = created_at  # Repetition 3
        self.last_login = last_login  # Repetition 4

    def to_dict(self):
        return {
            'username': self.username,      # Again
            'email': self.email,            # Again
            'created_at': self.created_at,  # Again
            'last_login': self.last_login,  # Again
        }
```

**Problem**: Add a new field? Update 3+ places. Rename a field? Search and replace carefully. Easy to miss something and introduce bugs.

## The XSynth Solution

**Define once, use everywhere:**

```python
#$define FIELDS username, email, created_at, last_login
#$define CLASS_NAME User

class $CLASS_NAME$:
    def __init__(self, $FIELDS$):
        # XSynth expands $FIELDS$ to the parameter list
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login
```

## How It Works

1. **Write `.xpy` file** with XSynth directives (`#$define`, `$name$`)
2. **Run XSynth preprocessor**: `python qdutils/xsynth.py`
3. **Get generated `.py` file** with substitutions applied
4. **Import and use** the standard Python file

## Example Files

- **user_model.xpy** - Source file with XSynth directives
- **user_model.py** - Generated output (readable Python)

## XSynth Syntax

### Define a Substitution

```python
#$define NAME value
```

- Must be at start of line
- NAME is your identifier
- value is what gets substituted

### Use a Substitution

```python
$NAME$            # Simple substitution
$"NAME$           # Quoted with "
$'NAME$           # Quoted with '
```

## Real-World Benefits

### Adding a Field

**Without XSynth**: Update `__init__`, `to_dict()`, SQL, validation, etc. (5-10 places)

**With XSynth**: Update `#$define FIELDS ...` (1 place), run preprocessor

### Refactoring

**Without XSynth**: Careful search-and-replace, hope you got them all

**With XSynth**: Change the `#$define`, regenerate

### Code Review

**Without XSynth**: "Did you update all the methods when you added that field?"

**With XSynth**: The preprocessor guarantees consistency

## Try It

```bash
# From the QuickDev root directory
python qdutils/xsynth.py

# Or process a specific directory
python qdutils/xsynth.py examples/xsynth-tutorial/
```

## Philosophy

XSynth extends DRY (Don't Repeat Yourself) from runtime to compile-time:

- **Runtime DRY**: Extract common code into functions/classes
- **Compile-time DRY**: Generate repetitive patterns from declarations

The generated code is readable, standard Python - no runtime magic, no performance overhead.

## When to Use XSynth

✓ Data models with many fields
✓ CRUD operations
✓ SQL generation
✓ Repetitive class patterns
✓ Template-based code generation

✗ Complex logic (use regular Python)
✗ One-off code (not worth the overhead)
✗ Simple applications (might be overkill)

## Advanced Features

XSynth can do much more than simple substitution:

- `#$ dict` declarations for data modeling
- `#$ action` declarations for class generation
- Module references: `module.name`
- Database tracking of dependencies

See the qdcore/*.xpy files for real-world examples of advanced usage.
