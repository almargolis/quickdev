# Stop Rewriting Authentication Code

## How Many Times Have You Written This?

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # 40 lines of validation, user creation, error handling...
```

If you're a Flask developer, you've written this code in **every single project**. Different apps, same boilerplate. Same validation logic. Same error handling. Same templates.

## The Madness of Repetition

I counted my projects. Over the past 5 years, I've implemented user authentication **23 times**. That's roughly **200 lines of code × 23 projects = 4,600 lines** of nearly identical authentication code.

Think about that. 4,600 lines of code that:
- Does the exact same thing
- Has the exact same bugs (until I fix them)
- Requires the exact same tests
- Takes the exact same 4 hours to implement

And I'm not alone. Every Flask developer does this. We copy-paste from our last project, tweak it slightly, hope we didn't introduce bugs in the migration, and move on.

**There has to be a better way.**

## The Dream: Authentication in One Line

What if it looked like this instead:

```python
from qdflask import init_auth

app = Flask(__name__)
db = SQLAlchemy(app)

init_auth(app, db)
```

That's it. One line. And you get:
- User model with email, password_hash, roles, is_active
- Login/logout routes with forms
- Registration with validation
- Password reset functionality
- Role-based access control
- CLI commands (flask user create, flask user add-role)
- Professional templates
- Session management
- Security best practices

## This Isn't a Framework

Before you roll your eyes thinking "oh great, another opinionated framework that does things I don't want," stop.

**QuickDev isn't a framework. It's a collection of idioms.**

It works **with** Flask, not instead of it. You still write Flask routes, use Flask extensions, and structure your app however you want. QuickDev just handles the boring, repetitive parts.

Think of it like this:
- **Flask** is the web framework
- **qdflask** is the auth idiom
- **Your app** is your unique business logic

## The Before & After

### Before: Traditional Implementation

**File: app.py (200+ lines)**

```python
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration Route (40 lines)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        # Validation
        if not email or not password:
            flash('Email and password required')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        # Check existing
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        # Create user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful!')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route (30 lines)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid credentials')
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Plus templates, CSS, CLI commands...
```

**Total: ~200 lines of boilerplate**

### After: QuickDev Idioms

**File: app.py (30 lines)**

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from qdflask import init_auth

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db = SQLAlchemy(app)

# One line gives you complete auth
init_auth(app, db)

# Now write your app-specific routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run()
```

**Total: ~30 lines**

**Reduction: 85%+**

## But What About Customization?

"Sure," you say, "but what if I need to customize the User model?"

Three options:

### 1. Configuration

```python
init_auth(app, db,
    user_fields=['username', 'bio', 'avatar_url'],
    roles=['admin', 'moderator', 'user', 'guest'],
    require_email_confirmation=True)
```

### 2. Subclass

```python
from qdflask.models import User as BaseUser

class User(BaseUser):
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(200))
    followers = db.relationship('User', ...)
```

### 3. Fork It

It's open source. Copy the code, modify it for your needs, make it **your** idiom for **your** projects.

## The Philosophy: Idioms, Not Frameworks

QuickDev is built on a simple idea: **You keep rewriting the same code.**

- User authentication? Written it 20 times.
- CRUD APIs? Written it 50 times.
- Image uploads? Written it 15 times.
- Email templates? Written it 30 times.

Each time, you either:
1. Copy-paste from your last project (risky)
2. Rewrite it from scratch (wasteful)
3. Use a massive framework (overkill)

QuickDev says: **Package your patterns once, use them everywhere.**

An **idiom** is a reusable pattern you've refined over years:
- qdflask = your authentication idiom
- qdimages = your image management idiom
- qdapi = your CRUD API idiom

## Real-World Impact

Here's what developers say after trying QuickDev:

> "I used to spend 4 hours setting up auth for every project. Now it takes 5 minutes. I can focus on the features that make my app unique." - Sarah, SaaS Founder

> "We have 12 Flask microservices. Before QuickDev, we had 12 slightly different auth implementations. Now they're all consistent, tested, and maintained in one place." - Mike, Engineering Lead

> "I thought I needed Django Admin for CRUD operations. Turns out I just needed the qdapi idiom - 80% less code, 100% of the functionality I needed." - Elena, Startup CTO

## Getting Started

### 1. Install

```bash
pip install qdflask
```

### 2. Use

```python
from qdflask import init_auth

init_auth(app, db)
```

### 3. Marvel

Your app now has production-ready authentication. For free.

### 4. Explore

Check out the other idioms:
- **qdimages** - Image management with storage, editing, metadata
- **qdapi** - RESTful CRUD APIs with filtering, search, validation
- **qdjobs** - Background job queue for async tasks
- **qdemail** - Template-based email sending

## The Bigger Picture

QuickDev isn't just about auth. It's about recognizing that **software development has patterns**, and those patterns should be **captured as code**.

You've spent years learning these patterns:
- How to structure a User model
- How to validate passwords
- How to handle sessions
- How to write secure login flows

Why rewrite them every time? Package them once. Use them forever.

## Try It

Clone the examples:

```bash
git clone https://github.com/quickdev/quickdev
cd quickdev/examples
./quickstart.sh
```

Run the before/after comparison. See **200 lines become 30 lines** with **identical functionality**.

Then ask yourself: "How much time have I wasted rewriting auth code?"

## Join the Movement

QuickDev is open source and actively looking for contributors. Have a pattern you rewrite constantly? Package it as an idiom. Share it with the community.

Together, we can stop rewriting the same code over and over.

**Because you have better things to build.**

---

## Resources

- **GitHub**: https://github.com/quickdev/quickdev
- **Examples**: https://github.com/quickdev/quickdev/tree/master/examples
- **Documentation**: https://quickdev.readthedocs.io
- **PyPI**: https://pypi.org/project/qdflask

## About QuickDev

QuickDev is a collection of idioms and code generation tools for Python developers. It's been in development since the 1990s, refined through decades of real-world use, and is now being released as open source.

The goal: **Help developers stop repeating themselves.**

---

*Ready to stop rewriting auth code? [Get started with QuickDev →](https://github.com/quickdev/quickdev)*
