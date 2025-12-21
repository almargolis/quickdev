"""
Flask Integration Example - QuickDev Idioms

This minimal Flask app demonstrates how QuickDev idioms eliminate boilerplate.
With just a few lines, you get:
- Complete user authentication system (qdflask)
- Full-featured image management (qdimages)
- All without writing CRUD code, forms, or database models
"""

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

# Standard Flask setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# QuickDev Idiom #1: Add complete authentication system
# Uncomment when qdflask is installed:
# from qdflask import init_auth
# init_auth(app, db)
#
# This single line gives you:
# - User model with role-based access control
# - Login/logout routes and forms
# - Password hashing
# - Session management
# - User management CLI commands

# QuickDev Idiom #2: Add image management system
# Uncomment when qdimages is installed:
# from qdimages import init_image_manager
# init_image_manager(app, db, storage_path='./image_storage')
#
# This single line gives you:
# - 16 RESTful API endpoints for image operations
# - Content-addressed storage with deduplication
# - Web-based image editor (crop, resize, brightness, etc.)
# - Metadata tracking with keywords and EXIF
# - Image model with database persistence


@app.route('/')
def index():
    return """
    <h1>QuickDev Flask Integration Example</h1>
    <p>This app demonstrates QuickDev idioms:</p>
    <ul>
        <li><strong>qdflask</strong>: Complete auth system in one line</li>
        <li><strong>qdimages</strong>: Full image management in one line</li>
    </ul>
    <p>See app.py source code to see how simple the integration is.</p>
    <hr>
    <h2>What You Get For Free:</h2>
    <h3>From qdflask:</h3>
    <ul>
        <li>User registration and login</li>
        <li>Role-based access control</li>
        <li>Password hashing</li>
        <li>CLI: flask user create, flask user add-role, etc.</li>
    </ul>
    <h3>From qdimages:</h3>
    <ul>
        <li>Upload, retrieve, update, delete images</li>
        <li>Image editing (crop, resize, brightness, background removal)</li>
        <li>Metadata and keyword management</li>
        <li>Content-addressed storage (automatic deduplication)</li>
    </ul>
    """


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
