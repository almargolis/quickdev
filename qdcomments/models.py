"""
Database models for qdcomments.

Provides Comment model for storing user comments with moderation support.

Note: This module imports the canonical db and User from qdflask.models to ensure
all Flask modules share the same database instance and User model.
"""

from datetime import datetime
from qdflask.models import db, User


class Comment(db.Model):
    """
    Comment model for content with moderation and threading support.

    Stores comments for any content type (articles, products, listings, etc.)
    with comprehensive moderation tracking and user permission snapshots.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        content_type: Type of content being commented on (e.g., 'article', 'product')
        content_id: ID or slug of the content (e.g., 'python/my-article')
        content: Comment text (raw, before processing)
        user_comment_style: Snapshot of user's comment_style at comment time ('t', 'h', 'm')
        user_moderation_level: Snapshot of user's moderation_level at comment time ('0', '1', '9')
        status: Comment status ('p'=posted, 'm'=moderation, 'b'=blocked)
        status_reason: Reason for status ('a'=automatic, 'm'=moderator, 'd'=blocked_words)
        parent_id: Foreign key to parent comment (for threading)
        created_at: When comment was created
        updated_at: When comment was last modified
        moderated_at: When comment was moderated
        moderated_by_id: User who moderated this comment

    Example:
        comment = Comment(
            user_id=1,
            content_type='article',
            content_id='python/intro',
            content='Great article!',
            user_comment_style='t',
            user_moderation_level='9',
            status='p',
            status_reason='a'
        )
        db.session.add(comment)
        db.session.commit()
    """
    __tablename__ = 'comments'

    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Content-agnostic reference (works for articles, products, etc.)
    content_type = db.Column(db.String(50), nullable=False, index=True)
    content_id = db.Column(db.String(255), nullable=False, index=True)

    # Comment content (raw text before processing)
    content = db.Column(db.Text, nullable=False)

    # Snapshot of user settings at comment time
    user_comment_style = db.Column(db.String(1), nullable=False)  # 't', 'h', 'm'
    user_moderation_level = db.Column(db.String(1), nullable=False)  # '0', '1', '9'

    # Status tracking
    status = db.Column(db.String(1), nullable=False, default='p', index=True)  # 'p', 'm', 'b', 'r'
    # Status values: 'p'=posted, 'm'=moderation, 'b'=blocked, 'r'=revoked
    status_reason = db.Column(db.String(1), nullable=False, default='a')  # 'a', 'm', 'd'
    # Reason values: 'a'=automatic, 'm'=moderator, 'd'=dirty_words

    # Threading support
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    moderated_at = db.Column(db.DateTime, nullable=True)
    moderated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    user = db.relationship(User, foreign_keys=[user_id], backref='comments')
    moderator = db.relationship(User, foreign_keys=[moderated_by_id])
    parent = db.relationship('Comment', remote_side=[id], backref='replies')

    # Composite indexes for common queries
    __table_args__ = (
        db.Index('idx_content_lookup', 'content_type', 'content_id', 'status'),
        db.Index('idx_moderation_queue', 'status', 'created_at'),
    )

    def __repr__(self):
        return f'<Comment {self.id} by user {self.user_id} on {self.content_type}/{self.content_id}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'content_type': self.content_type,
            'content_id': self.content_id,
            'content': self.content,
            'user_comment_style': self.user_comment_style,
            'status': self.status,
            'status_reason': self.status_reason,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'moderated_at': self.moderated_at.isoformat() if self.moderated_at else None,
        }

    @staticmethod
    def get_for_content(content_type, content_id, status='p', include_replies=True):
        """
        Get comments for specific content.

        Args:
            content_type: Type of content ('article', 'product', etc.)
            content_id: Content identifier
            status: Comment status to filter by (default: 'p' for posted)
            include_replies: Include threaded replies (default: True)

        Returns:
            Query object (call .all() or .paginate())
        """
        query = Comment.query.filter_by(
            content_type=content_type,
            content_id=content_id,
            status=status
        )

        if not include_replies:
            query = query.filter_by(parent_id=None)

        return query.order_by(Comment.created_at.desc())

    @staticmethod
    def count_for_content(content_type, content_id, status='p'):
        """
        Count comments for specific content.

        Args:
            content_type: Type of content
            content_id: Content identifier
            status: Comment status to count (default: 'p')

        Returns:
            Integer count
        """
        return Comment.query.filter_by(
            content_type=content_type,
            content_id=content_id,
            status=status
        ).count()

    @staticmethod
    def get_pending_moderation():
        """
        Get all comments pending moderation.

        Returns:
            Query object for comments with status='m'
        """
        return Comment.query.filter_by(status='m').order_by(Comment.created_at.desc())

    def approve(self, moderator_id):
        """
        Approve a comment (change status from 'm' to 'p').

        Args:
            moderator_id: ID of user approving the comment
        """
        self.status = 'p'
        self.status_reason = 'm'  # Moderator decision
        self.moderated_at = datetime.utcnow()
        self.moderated_by_id = moderator_id
        db.session.commit()

    def reject(self, moderator_id):
        """
        Reject a comment (change status from 'm' to 'b').

        Args:
            moderator_id: ID of user rejecting the comment
        """
        self.status = 'b'
        self.status_reason = 'm'  # Moderator decision
        self.moderated_at = datetime.utcnow()
        self.moderated_by_id = moderator_id
        db.session.commit()

    def revoke(self, moderator_id):
        """
        Revoke a comment (change status to 'r').
        Used when a previously approved comment needs to be removed.

        Args:
            moderator_id: ID of user revoking the comment
        """
        self.status = 'r'
        self.status_reason = 'm'  # Moderator decision
        self.moderated_at = datetime.utcnow()
        self.moderated_by_id = moderator_id
        db.session.commit()

    def set_status(self, new_status, moderator_id):
        """
        Change comment status.

        Args:
            new_status: New status ('p', 'm', 'b', or 'r')
            moderator_id: ID of user changing the status
        """
        if new_status not in ['p', 'm', 'b', 'r']:
            raise ValueError(f"Invalid status: {new_status}")

        self.status = new_status
        self.status_reason = 'm'  # Moderator decision
        self.moderated_at = datetime.utcnow()
        self.moderated_by_id = moderator_id
        db.session.commit()
