#!/usr/bin/env python3
"""
qdflask.cli - Command-line utilities for qdflask

Provides CLI commands for initializing database and managing users.
"""

import argparse
import sys


def init_db():
    """
    CLI entry point for qdflask-init command.

    Initializes the database and creates an admin user.

    Usage:
        qdflask-init --app myapp:app --admin-password secret123
    """
    parser = argparse.ArgumentParser(description='Initialize qdflask database')
    parser.add_argument('--app', type=str, required=True,
                        help='Flask app module:instance (e.g., myapp:app)')
    parser.add_argument('--admin-username', type=str, default='admin',
                        help='Username for admin user (default: admin)')
    parser.add_argument('--admin-password', type=str, default='admin',
                        help='Password for admin user (default: admin)')
    parser.add_argument('--roles', type=str,
                        help='Comma-separated list of roles (default: admin,editor)')
    args = parser.parse_args()

    # Import and get the app
    try:
        module_name, app_name = args.app.split(':')
        module = __import__(module_name, fromlist=[app_name])
        app = getattr(module, app_name)
    except Exception as e:
        print(f"Error loading app from {args.app}: {e}")
        return 1

    from qdflask.models import db, User

    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        admin = User.get_by_username(args.admin_username)

        if admin:
            print(f"Admin user '{args.admin_username}' already exists")
            print("Updating admin user...")
            admin.role = 'admin'
            admin.set_password(args.admin_password)
            admin.is_active = True
            db.session.commit()
            print("Admin user updated successfully")
        else:
            print(f"Creating admin user '{args.admin_username}'...")
            admin = User(username=args.admin_username, role='admin')
            admin.set_password(args.admin_password)

            db.session.add(admin)
            db.session.commit()

            print("Admin user created successfully")

        print()
        print(f"  Username: {args.admin_username}")
        print(f"  Password: {args.admin_password}")
        print("  Role: admin")

        if args.admin_password == 'admin':
            print("\n  IMPORTANT: Change the default password after first login!")

        # Display configured roles
        roles = app.config.get('QDFLASK_ROLES', ['admin', 'editor'])
        print(f"\nConfigured roles: {', '.join(roles)}")

        print("\nDatabase initialization complete")

    return 0


def create_user():
    """
    CLI entry point for qdflask-create-user command.

    Creates a new user.

    Usage:
        qdflask-create-user --app myapp:app --username john --password secret --role editor
    """
    parser = argparse.ArgumentParser(description='Create a new qdflask user')
    parser.add_argument('--app', type=str, required=True,
                        help='Flask app module:instance (e.g., myapp:app)')
    parser.add_argument('--username', type=str, required=True,
                        help='Username for new user')
    parser.add_argument('--password', type=str, required=True,
                        help='Password for new user')
    parser.add_argument('--role', type=str, default='editor',
                        help='Role for new user (default: editor)')
    args = parser.parse_args()

    # Import and get the app
    try:
        module_name, app_name = args.app.split(':')
        module = __import__(module_name, fromlist=[app_name])
        app = getattr(module, app_name)
    except Exception as e:
        print(f"Error loading app from {args.app}: {e}")
        return 1

    from qdflask.models import db, User

    with app.app_context():
        # Check if user exists
        existing_user = User.get_by_username(args.username)
        if existing_user:
            print(f"Error: User '{args.username}' already exists")
            return 1

        # Validate role
        roles = app.config.get('QDFLASK_ROLES', ['admin', 'editor'])
        if args.role not in roles:
            print(f"Error: Invalid role '{args.role}'")
            print(f"Valid roles: {', '.join(roles)}")
            return 1

        # Validate password
        if len(args.password) < 6:
            print("Error: Password must be at least 6 characters")
            return 1

        # Create user
        user = User(username=args.username, role=args.role)
        user.set_password(args.password)

        db.session.add(user)
        db.session.commit()

        print(f"User '{args.username}' created successfully")
        print(f"  Role: {args.role}")

    return 0


def list_users():
    """
    CLI entry point for qdflask-list-users command.

    Lists all users.

    Usage:
        qdflask-list-users --app myapp:app
    """
    parser = argparse.ArgumentParser(description='List all qdflask users')
    parser.add_argument('--app', type=str, required=True,
                        help='Flask app module:instance (e.g., myapp:app)')
    args = parser.parse_args()

    # Import and get the app
    try:
        module_name, app_name = args.app.split(':')
        module = __import__(module_name, fromlist=[app_name])
        app = getattr(module, app_name)
    except Exception as e:
        print(f"Error loading app from {args.app}: {e}")
        return 1

    from qdflask.models import User

    with app.app_context():
        users = User.get_all()

        if not users:
            print("No users found")
            return 0

        print(f"\nTotal users: {len(users)}\n")
        print(f"{'Username':<20} {'Role':<15} {'Active':<8} {'Last Login':<20}")
        print("-" * 70)

        for user in users:
            active = "Yes" if user.is_active else "No"
            last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
            print(f"{user.username:<20} {user.role:<15} {active:<8} {last_login:<20}")

    return 0


if __name__ == '__main__':
    # Allow running as a script
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        sys.argv.pop(1)
        sys.exit(init_db())
    elif len(sys.argv) > 1 and sys.argv[1] == 'create-user':
        sys.argv.pop(1)
        sys.exit(create_user())
    elif len(sys.argv) > 1 and sys.argv[1] == 'list-users':
        sys.argv.pop(1)
        sys.exit(list_users())
    else:
        print("Usage: python -m qdflask.cli [init|create-user|list-users] [options]")
        sys.exit(1)
