"""
qdflask - QuickDev Flask Authentication Package

A reusable Flask authentication package that provides user login, role-based
access control, and user management. Designed to be easily integrated into
any Flask application.

Usage:
    from qdflask import init_auth, create_admin_user
    from qdflask.models import db, User
    from qdflask.auth import auth_bp

    app = Flask(__name__)

    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

    # Initialize authentication
    init_auth(app, roles=['admin', 'editor', 'viewer'])

    # Register authentication blueprint
    app.register_blueprint(auth_bp)

    # Create admin user on first run
    with app.app_context():
        create_admin_user('admin', 'password123')
"""

from flask_login import LoginManager

__version__ = '0.1.0'
__all__ = ['init_auth', 'create_admin_user', 'require_role']

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from qdflask.models import User
    return User.get(user_id)


def init_auth(app, roles=None, login_view='auth.login',
              db_path='passwords.db'):
    """
    Initialize authentication for a Flask application.

    Args:
        app: Flask application instance
        roles: List of valid role names. Must include 'admin'.
               Defaults to ['admin', 'editor']
        login_view: The view to redirect to when login is required
        db_path: Path to the passwords database file.
                 Defaults to 'passwords.db'.

    Example:
        init_auth(app, roles=['admin', 'manager', 'staff', 'customer'])
    """
    from qdflask.models import db

    if roles is None:
        roles = ['admin', 'editor']

    if 'admin' not in roles:
        raise ValueError("roles must include 'admin'")

    # Store valid roles in app config
    app.config['QDFLASK_ROLES'] = roles

    # Set database URI from db_path
    app.config.setdefault(
        'SQLALCHEMY_DATABASE_URI', f'sqlite:///{db_path}')

    # Initialize database
    db.init_app(app)

    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = login_view

    # Create tables and seed admin user on first run
    with app.app_context():
        db.create_all()
        from qdflask.models import User
        if User.query.count() == 0:
            create_admin_user()
            app.logger.info(
                "Created initial admin user (admin/admin)"
                " - change password after first login"
            )


def create_admin_user(username='admin', password='admin'):
    """
    Create or update the admin user.

    Must be called within app context.

    Args:
        username: Username for admin user
        password: Password for admin user

    Returns:
        User object

    Example:
        with app.app_context():
            admin = create_admin_user('admin', 'secure_password')
    """
    from qdflask.models import db, User

    admin = User.get_by_username(username)

    if admin:
        # Update existing admin
        admin.role = 'admin'
        admin.set_password(password)
        admin.is_active = True
    else:
        # Create new admin
        admin = User(username=username, role='admin')
        admin.set_password(password)
        db.session.add(admin)

    db.session.commit()
    return admin


def require_role(*roles):
    """
    Decorator to require specific roles for a route.

    Args:
        *roles: One or more role names required to access the route

    Example:
        @app.route('/admin')
        @login_required
        @require_role('admin')
        def admin_panel():
            return "Admin panel"

        @app.route('/edit')
        @login_required
        @require_role('admin', 'editor')
        def edit_content():
            return "Edit content"
    """
    from functools import wraps
    from flask import abort
    from flask_login import current_user

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
