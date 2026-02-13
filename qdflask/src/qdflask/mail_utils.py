"""
qdflask.email - Email utility module

Provides email sending functionality for Flask applications using Flask-Mail.
Supports any SMTP provider (Brevo, SendGrid, Gmail, Mailgun, etc.) via configuration.
"""

from flask_mail import Mail, Message
from flask import current_app
import logging
from qdbase.qdconf import QdConf

mail = Mail()

def init_mail(app, config_path=None):
    """
    Initialize Flask-Mail with the app.

    Args:
        app: Flask application instance
        config_path: Optional explicit conf directory path (default: auto-detect)

    Configuration is loaded from:
        1. conf/email.toml - SMTP server settings
        2. conf/.env - SMTP_PW (password/API key)

    Example conf/email.toml:
        MAIL_SERVER = "smtp-relay.brevo.com"
        MAIL_PORT = 587
        MAIL_USE_TLS = true
        MAIL_USE_SSL = false
        MAIL_USERNAME = "your-email@example.com"
        MAIL_DEFAULT_SENDER = "noreply@yourdomain.com"

    Example conf/.env:
        SMTP_PW=your-smtp-password-or-api-key

    """
    # Initialize QdConf with optional explicit path
    conf = QdConf(conf_dir=config_path)

    # Load SMTP password from .env
    smtp_password = conf.get('denv.SMTP_PW')

    # Apply configuration using QdConf with defaults
    app.config.setdefault('MAIL_SERVER', conf.get('email.MAIL_SERVER', 'localhost'))
    app.config.setdefault('MAIL_PORT', conf.get('email.MAIL_PORT', 587))
    app.config.setdefault('MAIL_USE_TLS', conf.get('email.MAIL_USE_TLS', True))
    app.config.setdefault('MAIL_USE_SSL', conf.get('email.MAIL_USE_SSL', False))
    app.config.setdefault('MAIL_USERNAME', conf.get('email.MAIL_USERNAME', ''))
    app.config.setdefault('MAIL_DEFAULT_SENDER', conf.get('email.MAIL_DEFAULT_SENDER', 'noreply@example.com'))

    # Set password from .env
    if smtp_password:
        app.config['MAIL_PASSWORD'] = smtp_password

    mail.init_app(app)
    return mail


def send_email(subject, recipients, body, sender=None):
    """
    Send a plain text email.

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses or single email string
        body: Plain text email body
        sender: Optional sender email (defaults to MAIL_DEFAULT_SENDER)

    Returns:
        bool: True if sent successfully, False otherwise

    Example:
        send_email(
            subject="New Comment for Moderation",
            recipients=["admin@example.com"],
            body="A new comment is pending moderation."
        )
    """
    if not current_app.config.get('MAIL_SERVER'):
        logging.warning("Email not configured - skipping send")
        return False

    # Convert single recipient to list
    if isinstance(recipients, str):
        recipients = [recipients]

    # Filter out empty recipients
    recipients = [r for r in recipients if r and r.strip()]

    if not recipients:
        logging.warning("No valid recipients - skipping email")
        return False

    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            sender=sender or current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        logging.info(f"Email sent: {subject} to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False


def get_verified_admin_emails():
    """
    Get list of verified admin email addresses.

    Returns:
        List of email addresses for admins with email_verified='Y'

    Example:
        admins = get_verified_admin_emails()
        send_email("Alert", admins, "Something happened")
    """
    from qdflask.models import User

    admin_users = User.get_verified_admins()
    return [user.email_address for user in admin_users if user.email_address]


def send_to_admins(subject, body, sender=None):
    """
    Send email to all verified admins.

    Args:
        subject: Email subject line
        body: Plain text email body
        sender: Optional sender email

    Returns:
        bool: True if sent successfully, False otherwise

    Example:
        send_to_admins(
            subject="New Comment Pending Moderation",
            body="A new comment requires your review."
        )
    """
    recipients = get_verified_admin_emails()

    if not recipients:
        logging.info("No verified admin emails - skipping notification")
        return False

    return send_email(subject, recipients, body, sender)
