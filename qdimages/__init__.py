"""
qdimages - QuickDev Image Management Package

A reusable Flask image management package that provides image upload, editing,
hierarchical hash-based storage, metadata tracking, and a web-based image editor.
Designed to be easily integrated into any Flask application.

Features:
- Hierarchical xxHash-based storage with content addressing
- Image editor with crop, resize, brightness/contrast, background removal
- Metadata tracking (keywords, dimensions, format, EXIF)
- Browse and search capabilities
- Automatic duplicate detection
- Source tracking for edited images

Usage:
    from flask import Flask
    from qdimages import init_image_manager

    app = Flask(__name__)

    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

    # Initialize image manager
    init_image_manager(app, {
        'IMAGES_BASE_PATH': './images',
        'TEMP_IMAGES_PATH': './temp_images',
        'TEMP_DIRECTORY': '/tmp/app_images',
        'UPLOAD_FOLDER': './uploads',
        'MAX_CONTENT_LENGTH': 10 * 1024 * 1024  # 10MB
    })

    if __name__ == '__main__':
        app.run(debug=True)
"""

from flask import Blueprint

__version__ = '0.1.0'
__all__ = ['init_image_manager', 'image_bp']

# Blueprint for image routes
image_bp = Blueprint(
    'images',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix=''  # No prefix, routes define their own paths
)


def init_image_manager(app, config=None, db_instance=None):
    """
    Initialize image management for a Flask application.

    Args:
        app: Flask application instance
        config: Dictionary of configuration options:
            - IMAGES_BASE_PATH: Path for hierarchical image storage (default: './images')
            - TEMP_IMAGES_PATH: Path for staging area (default: './temp_images')
            - TEMP_DIRECTORY: Path for temporary processing (default: '/tmp/qdimages_temp')
            - UPLOAD_FOLDER: Path for uploaded files (default: './uploads')
            - MAX_CONTENT_LENGTH: Max upload size in bytes (default: 10MB)
            - ALLOWED_EXTENSIONS: Set of allowed file extensions (default: {'png', 'jpg', 'jpeg', 'gif'})
        db_instance: Optional SQLAlchemy db instance to use (if app already has one)

    Returns:
        None

    Example:
        >>> from flask import Flask
        >>> from qdimages import init_image_manager
        >>> app = Flask(__name__)
        >>> init_image_manager(app, {
        ...     'IMAGES_BASE_PATH': '/var/www/images',
        ...     'MAX_CONTENT_LENGTH': 20 * 1024 * 1024  # 20MB
        ... })
    """
    import os
    from qdimages.models import init_db, use_existing_db

    # Default configuration
    defaults = {
        'IMAGES_BASE_PATH': os.path.join(os.getcwd(), 'images'),
        'TEMP_IMAGES_PATH': os.path.join(os.getcwd(), 'temp_images'),
        'TEMP_DIRECTORY': '/tmp/qdimages_temp',
        'UPLOAD_FOLDER': os.path.join(os.getcwd(), 'uploads'),
        'MAX_CONTENT_LENGTH': 10 * 1024 * 1024,  # 10MB
        'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif'}
    }

    # Merge user config with defaults
    if config:
        defaults.update(config)

    # Apply configuration to app
    for key, value in defaults.items():
        app.config.setdefault(key, value)

    # Create directories if they don't exist
    os.makedirs(app.config['IMAGES_BASE_PATH'], exist_ok=True)
    os.makedirs(app.config['TEMP_IMAGES_PATH'], exist_ok=True)
    os.makedirs(app.config['TEMP_DIRECTORY'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize or use existing database
    if db_instance:
        use_existing_db(db_instance)
        # Create Image table if it doesn't exist
        with app.app_context():
            db_instance.create_all()
    else:
        init_db(app)

    # Import and register routes
    from qdimages import routes
    app.register_blueprint(image_bp)

    app.logger.info(f"qdimages initialized (v{__version__})")
    app.logger.info(f"  Images path: {app.config['IMAGES_BASE_PATH']}")
    app.logger.info(f"  Temp path: {app.config['TEMP_DIRECTORY']}")
