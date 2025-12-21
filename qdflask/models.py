"""
qdflask.models - Database models for authentication

Provides User model and database instance for Flask-SQLAlchemy.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.

    Attributes:
        id: Primary key
        username: Unique username
        password_hash: Hashed password (never store plain text)
        role: User role (e.g., 'admin', 'editor', 'viewer')
        created_at: Timestamp when user was created
        last_login: Timestamp of last successful login
        is_active: Whether the user account is active

    Example:
        user = User(username='john', role='editor')
        user.set_password('secret123')
        db.session.add(user)
        db.session.commit()
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='editor')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """
        Hash and set the user's password.

        Args:
            password: Plain text password to hash
        """
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """
        Check if the provided password matches the hash.

        Args:
            password: Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """
        Check if user has admin role.

        Returns:
            bool: True if user is admin
        """
        return self.role == 'admin'

    def has_role(self, *roles):
        """
        Check if user has any of the specified roles.

        Args:
            *roles: One or more role names to check

        Returns:
            bool: True if user has any of the specified roles

        Example:
            if user.has_role('admin', 'editor'):
                # User can edit
        """
        return self.role in roles

    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def get(user_id):
        """
        Get user by ID.

        Args:
            user_id: User ID to retrieve

        Returns:
            User object or None
        """
        return User.query.get(int(user_id))

    @staticmethod
    def get_by_username(username):
        """
        Get user by username.

        Args:
            username: Username to search for

        Returns:
            User object or None
        """
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_all_active():
        """
        Get all active users.

        Returns:
            List of active User objects
        """
        return User.query.filter_by(is_active=True).order_by(User.username).all()

    @staticmethod
    def get_all():
        """
        Get all users (including inactive).

        Returns:
            List of all User objects
        """
        return User.query.order_by(User.username).all()

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
