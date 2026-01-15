#!/usr/bin/env python3
"""
CLI tools for qdcomments.

Provides command-line utilities for database migration, initialization,
and comment moderation.
"""

import argparse
import os
import sys
from datetime import datetime


def load_app(app_string):
    """
    Load Flask app from string like 'myapp:create_app' or 'myapp:app'.

    Args:
        app_string: String in format 'module:app' or 'module:factory_function'

    Returns:
        Flask application instance
    """
    try:
        module_name, app_name = app_string.split(':')
        module = __import__(module_name, fromlist=[app_name])
        app_or_factory = getattr(module, app_name)

        # Check if it's a factory function
        if callable(app_or_factory):
            app = app_or_factory()
        else:
            app = app_or_factory

        return app
    except Exception as e:
        print(f"Error loading app from '{app_string}': {e}")
        sys.exit(1)


def migrate_user_table():
    """
    Add comment_style and moderation_level columns to users table.
    Sets defaults based on role (admin/editor → 'm'/'9', others → 't'/'1').
    """
    parser = argparse.ArgumentParser(
        description='Migrate users table to add comment fields'
    )
    parser.add_argument('--app', required=True, help='Flask app (e.g., myapp:create_app)')

    args = parser.parse_args()
    app = load_app(args.app)

    with app.app_context():
        from qdflask.models import db, User

        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        if 'comment_style' not in columns or 'moderation_level' not in columns:
            print("Adding comment_style and moderation_level columns...")

            # SQLite doesn't support adding columns with defaults in ALTER TABLE
            # So we use raw SQL
            try:
                if 'comment_style' not in columns:
                    db.engine.execute("ALTER TABLE users ADD COLUMN comment_style VARCHAR(1) DEFAULT 't'")
                    print("✓ Added comment_style column")

                if 'moderation_level' not in columns:
                    db.engine.execute("ALTER TABLE users ADD COLUMN moderation_level VARCHAR(1) DEFAULT '1'")
                    print("✓ Added moderation_level column")

                # Update existing users based on role
                admins_editors = User.query.filter(User.role.in_(['admin', 'editor'])).all()
                for user in admins_editors:
                    user.comment_style = 'm'
                    user.moderation_level = '9'

                db.session.commit()
                print(f"✓ Updated {len(admins_editors)} admin/editor users to markdown + auto-approved")

                print("\nMigration complete!")

            except Exception as e:
                print(f"Error during migration: {e}")
                db.session.rollback()
                sys.exit(1)
        else:
            print("Columns already exist. No migration needed.")


def init_blocked_words_file():
    """
    Initialize blocked_words.yaml file.
    """
    parser = argparse.ArgumentParser(
        description='Initialize blocked_words.yaml file'
    )
    parser.add_argument('--app', required=True, help='Flask app (e.g., myapp:create_app)')
    parser.add_argument('--path', help='Custom path for blocked_words.yaml')

    args = parser.parse_args()
    app = load_app(args.app)

    with app.app_context():
        if args.path:
            path = args.path
        else:
            path = app.config.get('BLOCKED_WORDS_PATH')

        if os.path.exists(path):
            print(f"File already exists: {path}")
            response = input("Overwrite? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                sys.exit(0)

        from qdcomments.filters import initialize_blocked_words
        initialize_blocked_words(path)
        print(f"✓ Created blocked_words.yaml at {path}")


def list_pending_comments():
    """
    List all pending comments from CLI.
    """
    parser = argparse.ArgumentParser(
        description='List pending comments'
    )
    parser.add_argument('--app', required=True, help='Flask app (e.g., myapp:create_app)')

    args = parser.parse_args()
    app = load_app(args.app)

    with app.app_context():
        from qdcomments.models import Comment

        pending = Comment.get_pending_moderation().all()

        if not pending:
            print("No pending comments.")
            sys.exit(0)

        print(f"\nPending comments ({len(pending)}):")
        print("-" * 80)

        for comment in pending:
            print(f"\nID: {comment.id}")
            print(f"User: {comment.user.username if comment.user else 'Unknown'}")
            print(f"Content: {comment.content_type}/{comment.content_id}")
            print(f"Created: {comment.created_at}")
            print(f"Reason: {comment.status_reason}")
            print(f"Text: {comment.content[:100]}...")
            print("-" * 80)


def approve_comment_cli():
    """
    Approve a comment from CLI.
    """
    parser = argparse.ArgumentParser(
        description='Approve a comment'
    )
    parser.add_argument('--app', required=True, help='Flask app (e.g., myapp:create_app)')
    parser.add_argument('--id', type=int, required=True, help='Comment ID to approve')
    parser.add_argument('--moderator-id', type=int, default=1, help='Moderator user ID (default: 1)')

    args = parser.parse_args()
    app = load_app(args.app)

    with app.app_context():
        from qdcomments.models import Comment

        comment = Comment.query.get(args.id)
        if not comment:
            print(f"Comment {args.id} not found.")
            sys.exit(1)

        if comment.status != 'm':
            print(f"Comment {args.id} is not pending moderation (status: {comment.status}).")
            sys.exit(1)

        comment.approve(args.moderator_id)
        print(f"✓ Comment {args.id} approved.")


def reject_comment_cli():
    """
    Reject a comment from CLI.
    """
    parser = argparse.ArgumentParser(
        description='Reject a comment'
    )
    parser.add_argument('--app', required=True, help='Flask app (e.g., myapp:create_app)')
    parser.add_argument('--id', type=int, required=True, help='Comment ID to reject')
    parser.add_argument('--moderator-id', type=int, default=1, help='Moderator user ID (default: 1)')

    args = parser.parse_args()
    app = load_app(args.app)

    with app.app_context():
        from qdcomments.models import Comment

        comment = Comment.query.get(args.id)
        if not comment:
            print(f"Comment {args.id} not found.")
            sys.exit(1)

        if comment.status != 'm':
            print(f"Comment {args.id} is not pending moderation (status: {comment.status}).")
            sys.exit(1)

        comment.reject(args.moderator_id)
        print(f"✓ Comment {args.id} rejected.")


if __name__ == '__main__':
    print("Use the entry points defined in setup.py instead:")
    print("  qdcomments-migrate-users --app myapp:app")
    print("  qdcomments-init-blocked-words --app myapp:app")
    print("  qdcomments-pending --app myapp:app")
    print("  qdcomments-approve --app myapp:app --id 123")
    print("  qdcomments-reject --app myapp:app --id 123")
