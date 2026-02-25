"""
Database models for qdimages.

Provides SQLAlchemy models for image metadata storage.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the Flask app."""
    if 'sqlalchemy' not in app.extensions:
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


class ImageExif(db.Model):
    """
    EXIF metadata extracted from images.

    Stores individual EXIF tags as separate records for flexible querying.
    """
    __tablename__ = 'image_exif'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False, index=True)
    tag_name = db.Column(db.String(100), nullable=False)
    tag_value = db.Column(db.Text)

    # Relationship
    image = db.relationship('Image', backref='exif_tags')

    def __repr__(self):
        return f'<ImageExif {self.tag_name}={self.tag_value[:50]}>'


class SourceTracking(db.Model):
    """
    Tracks source images and transformations for edited images.

    When an image is edited (cropped, resized, etc.), this table records
    the source image and what transformations were applied.
    """
    __tablename__ = 'source_tracking'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False, index=True)
    source_image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    transformations = db.Column(db.Text)  # JSON string of transformations applied

    # Relationships
    image = db.relationship('Image', foreign_keys=[image_id], backref='source_tracking_records')
    source_image = db.relationship('Image', foreign_keys=[source_image_id])

    def __repr__(self):
        return f'<SourceTracking image_id={self.image_id} source={self.source_image_id}>'
