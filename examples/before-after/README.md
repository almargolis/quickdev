# Before/After Comparison

This example demonstrates the dramatic reduction in boilerplate when using QuickDev idioms.

## The Challenge

Build a Flask app with user authentication:
- User registration
- Login/logout
- Protected routes
- Password hashing
- Session management
- CLI tools

## Traditional Approach: 200+ Lines

See `before_manual.py` for the full implementation.

**What you have to write:**
```python
# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    # ... more fields, methods, etc.

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Validation
    # Check if user exists
    # Create user
    # ... 40+ lines of code

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Authenticate user
    # Handle sessions
    # ... 30+ lines of code

# And more routes, templates, CLI commands...
```

**Total: ~200 lines** (and this is simplified!)

## QuickDev Approach: 30 Lines

See `after_quickdev.py` for the full implementation.

**What you have to write:**
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from qdflask import init_auth

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

# One line of code gives you everything:
init_auth(app, db)

# That's it! Write your app-specific routes now.
```

**Total: ~30 lines**

## The Difference

| Aspect | Manual | QuickDev | Savings |
|--------|--------|----------|---------|
| **Lines of code** | 200+ | 30 | 85%+ |
| **User model** | Write it | Generated | ✓ |
| **Login route** | Write it | Generated | ✓ |
| **Register route** | Write it | Generated | ✓ |
| **Templates** | Write them | Generated | ✓ |
| **Validation** | Write it | Generated | ✓ |
| **CLI commands** | Write them | Generated | ✓ |
| **Password hashing** | Set it up | Built-in | ✓ |
| **Session management** | Configure it | Built-in | ✓ |
| **Role-based access** | Implement it | Built-in | ✓ |

## Run the Examples

```bash
# Traditional approach
python before_manual.py
# Visit http://localhost:5001

# QuickDev approach (when qdflask is installed)
python after_quickdev.py
# Visit http://localhost:5002
```

Both apps have identical functionality!

## The Point

QuickDev doesn't replace Flask - it eliminates the repetitive parts:

**Traditional workflow:**
1. Read Flask-Login docs
2. Copy-paste boilerplate from tutorial
3. Modify for your needs
4. Write tests
5. Repeat for every new project

**QuickDev workflow:**
1. `init_auth(app, db)`
2. Write your application logic

## What About Customization?

"But what if I need to customize the User model?"

QuickDev idioms are **idioms**, not black boxes:

**Option 1: Configuration**
```python
init_auth(app, db,
    user_fields=['username', 'bio', 'avatar'],
    roles=['admin', 'moderator', 'user'])
```

**Option 2: Subclass**
```python
from qdflask.models import User as BaseUser

class User(BaseUser):
    bio = db.Column(db.Text)
    # Add your custom fields
```

**Option 3: Fork the idiom**
- Copy the qdflask code
- Modify it for your needs
- Now it's YOUR idiom for YOUR projects

## Philosophy

QuickDev captures **patterns you've already written 100 times**:

- User authentication? You've written it.
- Image upload with thumbnails? You've written it.
- CRUD operations? You've written it.

Stop rewriting the same code. Use idioms.

## Real-World Impact

**Time savings:**
- Setup auth: 4 hours → 5 minutes
- Setup image management: 6 hours → 10 minutes
- Build CRUD API: 3 hours → 30 minutes

**Quality improvements:**
- Tested idioms vs. rushed project code
- Security best practices baked in
- Consistent patterns across projects

**Mental overhead reduction:**
- "How did I implement password reset last time?"
- "Where's that decorator I wrote for role checking?"
- "Did I remember to hash passwords properly?"

→ All gone. The idiom handles it.

## Try It Yourself

1. Look at `before_manual.py` - notice all the repetition
2. Look at `after_quickdev.py` - notice what's missing
3. Run both - confirm identical functionality
4. Ask yourself: "How many times have I written this auth code?"

QuickDev is for developers who are tired of writing the same boilerplate over and over.
