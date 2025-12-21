"""
Tests for qdflask authentication module.
"""

import pytest
from flask import Flask
from qdflask import init_auth, create_admin_user
from qdflask.models import User, db


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    init_auth(app, roles=['admin', 'editor', 'viewer'])

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_init_auth(app):
    """Test that authentication initialization works."""
    assert app.config['TESTING'] is True
    assert 'sqlalchemy' in app.extensions


def test_create_admin_user(app):
    """Test creating an admin user."""
    with app.app_context():
        create_admin_user('admin', 'password123')
        user = User.get_by_username('admin')
        assert user is not None
        assert user.username == 'admin'
        assert user.role == 'admin'
        assert user.check_password('password123')


def test_user_password_hashing(app):
    """Test password hashing and verification."""
    with app.app_context():
        user = User(username='testuser', role='viewer')
        user.set_password('secret123')
        db.session.add(user)
        db.session.commit()

        assert user.check_password('secret123')
        assert not user.check_password('wrongpassword')


def test_user_roles(app):
    """Test user role checking."""
    with app.app_context():
        admin = User(username='admin', role='admin')
        editor = User(username='editor', role='editor')

        assert admin.is_admin()
        assert not editor.is_admin()

        assert admin.has_role('admin')
        assert editor.has_role('editor')
        assert not editor.has_role('admin')
