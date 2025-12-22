"""
qdcomments - QuickDev Commenting Package

A reusable Flask commenting system with sophisticated moderation, user permissions,
and content filtering. Designed to be easily integrated into any Flask application.

Features:
- User-level comment style permissions (text, HTML, markdown)
- Three-tier moderation system (blocked, requires approval, auto-approved)
- blocked_words filtering with configurable YAML list
- Content-agnostic design (works with articles, products, listings, etc.)
- Comment threading support
- Global moderation dashboard
- Admin interface for configuration

Usage:
    from flask import Flask
    from qdflask import init_auth
    from qdcomments import init_comments

    app = Flask(__name__)

    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['DATA_DIR'] = '/path/to/data'

    # Initialize authentication (qdflask owns db and User model)
    init_auth(app)

    # Initialize commenting (shares qdflask's db)
    init_comments(app, config={
        'COMMENTS_ENABLED': True,
        'BLOCKED_WORDS_PATH': '/path/to/blocked_words.yaml'
    })

    if __name__ == '__main__':
        app.run(debug=True)
"""

from flask import Blueprint
import os

__version__ = '0.1.0'
__all__ = ['init_comments', 'comments_bp']

# Blueprint for comment routes
comments_bp = Blueprint(
    'comments',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/comments'
)


def init_comments(app, config=None):
    """
    Initialize commenting system for a Flask application.

    Note: This must be called AFTER init_auth() from qdflask, as qdcomments
    shares qdflask's database instance and User model.

    Args:
        app: Flask application instance
        config: Dictionary of configuration options:
            - COMMENTS_ENABLED: Enable/disable comments globally (default: True)
            - COMMENTS_REQUIRE_LOGIN: Require login to comment (default: True)
            - BLOCKED_WORDS_PATH: Path to blocked_words.yaml (default: DATA_DIR/blocked_words.yaml)
            - COMMENTS_PER_PAGE: Pagination limit (default: 50)
            - COMMENT_MAX_LENGTH: Max comment length (default: 5000)
            - ALLOW_THREADING: Enable comment replies (default: True)
            - MAX_THREAD_DEPTH: Maximum nesting level (default: 3)

    Returns:
        None

    Example:
        >>> from qdflask import init_auth
        >>> from qdcomments import init_comments
        >>> init_auth(app)  # Initialize qdflask first
        >>> init_comments(app, config={
        ...     'COMMENTS_ENABLED': True,
        ...     'BLOCKED_WORDS_PATH': '/var/www/data/blocked_words.yaml'
        ... })
    """
    # Default configuration
    data_dir = app.config.get('DATA_DIR', os.getcwd())
    defaults = {
        'COMMENTS_ENABLED': True,
        'COMMENTS_REQUIRE_LOGIN': True,
        'BLOCKED_WORDS_PATH': os.path.join(data_dir, 'blocked_words.yaml'),
        'COMMENTS_PER_PAGE': 50,
        'COMMENT_MAX_LENGTH': 5000,
        'ALLOW_THREADING': True,
        'MAX_THREAD_DEPTH': 3,
    }

    # Merge user config with defaults
    if config:
        defaults.update(config)

    # Apply configuration to app
    for key, value in defaults.items():
        app.config.setdefault(key, value)

    # Import models (db and User are already imported from qdflask.models)
    from qdcomments.models import Comment, db

    # Create Comment table if it doesn't exist
    # (db was already initialized by qdflask's init_auth)
    with app.app_context():
        db.create_all()

    # Initialize blocked_words.yaml if doesn't exist
    blocked_words_path = app.config['BLOCKED_WORDS_PATH']
    if not os.path.exists(blocked_words_path):
        from qdcomments.filters import initialize_blocked_words
        initialize_blocked_words(blocked_words_path)
        app.logger.info(f"Created default blocked_words.yaml at {blocked_words_path}")

    # Import and register routes
    from qdcomments import routes

    # Register blueprint
    app.register_blueprint(comments_bp)

    app.logger.info(f"qdcomments initialized (v{__version__})")
    app.logger.info(f"  Comments enabled: {app.config['COMMENTS_ENABLED']}")
    app.logger.info(f"  Blocked words: {blocked_words_path}")
    app.logger.info(f"  Threading: {app.config['ALLOW_THREADING']}")
