"""
Database models for qdimages.

Provides SQLAlchemy models for image metadata storage.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the Flask app."""
    db.init_app(app)

    with app.app_context():
        db.create_all()


def use_existing_db(db_instance):
    """Use an existing SQLAlchemy db instance instead of creating a new one."""
    global db
    db = db_instance


class Image(db.Model):
    """
    Image metadata model for hierarchical storage.

    Stores metadata for images in the hash-based hierarchical storage system.
    Each image is identified by its xxHash and stored in a dir1/dir2/sequence.ext structure.
    """
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    xxhash = db.Column(db.String(16), unique=True, nullable=False, index=True)
    sha1 = db.Column(db.String(40), index=True)  # SHA1 hash for legacy compatibility

    # Hierarchical path components
    dir1 = db.Column(db.String(2), nullable=False, index=True)
    dir2 = db.Column(db.String(2), nullable=False, index=True)
    sequence_num = db.Column(db.Integer, nullable=False)  # Sequence number within dir1/dir2
    filename = db.Column(db.String(255), nullable=False)  # e.g., "1.jpg", "2.png"

    # Image properties
    format = db.Column(db.String(10))  # JPEG, PNG, GIF, etc.
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    file_size = db.Column(db.Integer)  # in bytes

    # Metadata
    keywords = db.Column(db.Text)  # Space-separated keywords
    has_exif = db.Column(db.Boolean, default=False)  # Whether image has EXIF data
    exif_data = db.Column(db.Text)  # JSON string of EXIF data

    # Source tracking for edited images
    source_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=True)
    transformations = db.Column(db.Text)  # JSON string of edits applied

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # User tracking (optional, requires user_id from auth system)
    user_id = db.Column(db.Integer, nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)  # User who created/uploaded the image

    # Relationships
    source_image = db.relationship('Image', remote_side=[id], backref='derived_images')

    def __repr__(self):
        return f'<Image {self.dir1}/{self.dir2}/{self.filename}>'


class DirectorySequence(db.Model):
    """
    Tracks the next available sequence number for each directory.

    Used to generate unique filenames within each dir1/dir2 directory pair.
    """
    __tablename__ = 'directory_sequence'

    id = db.Column(db.Integer, primary_key=True)
    dir1 = db.Column(db.String(2), nullable=False)
    dir2 = db.Column(db.String(2), nullable=False)
    next_sequence = db.Column(db.Integer, nullable=False, default=1)

    # Composite unique constraint on dir1+dir2
    __table_args__ = (
        db.UniqueConstraint('dir1', 'dir2', name='uq_dir1_dir2'),
    )

    def __repr__(self):
        return f'<DirectorySequence {self.dir1}/{self.dir2} next={self.next_sequence}>'

    @property
    def path(self):
        """Return the relative path: dir1/dir2/filename"""
        return f"{self.dir1}/{self.dir2}/{self.filename}"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'xxhash': self.xxhash,
            'path': self.path,
            'format': self.format,
            'width': self.width,
            'height': self.height,
            'file_size': self.file_size,
            'keywords': self.keywords,
            'source_image_id': self.source_image_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
