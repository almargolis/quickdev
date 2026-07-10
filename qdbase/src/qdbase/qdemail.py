"""
qdemail - Standalone SMTP email sending using Python's smtplib.

No Flask dependency. Works from CLI tools, cron jobs, and any Python context.

Configuration is loaded from conf/qdemail.toml + conf/.env via QdConf.

Example usage:
    from qdbase.qdemail import send_email

    # Auto-initializes from conf/qdemail.toml on first use
    send_email("Subject", ["user@example.com"], "Hello!")

    # Or initialize explicitly with a specific conf directory
    from qdbase.qdemail import init_email
    init_email(conf_dir="/path/to/mysite")
    send_email("Subject", ["user@example.com"], "Hello!")
"""

import os
import smtplib
import logging
import mimetypes
from dataclasses import dataclass
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from qdbase.qdconf import QdConf


@dataclass
class SmtpConfig:
    """SMTP connection parameters."""
    server: str = 'localhost'
    port: int = 587
    use_tls: bool = True
    username: str = ''
    password: str = ''
    default_sender: str = 'noreply@example.com'


# Module-level default config (set by init_email)
_config = None


def init_email(conf_dir=None):
    """
    Load SMTP configuration from conf/qdemail.toml and conf/.env.

    Args:
        conf_dir: Optional explicit conf directory path (default: auto-detect)

    Returns:
        SmtpConfig instance

    Configuration keys (in conf/qdemail.toml):
        MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_DEFAULT_SENDER

    Password (in conf/.env):
        SMTP_PW
    """
    global _config
    conf = QdConf(conf_dir=conf_dir)

    _config = SmtpConfig(
        server=conf.get('qdemail.MAIL_SERVER', 'localhost'),
        port=int(conf.get('qdemail.MAIL_PORT', 587)),
        use_tls=conf.get('qdemail.MAIL_USE_TLS', True),
        username=conf.get('qdemail.MAIL_USERNAME', ''),
        password=conf.get('denv.SMTP_PW', ''),
        default_sender=conf.get(
            'qdemail.MAIL_DEFAULT_SENDER', 'noreply@example.com'),
    )
    return _config


def send_email(subject, recipients, body, sender=None, config=None,
               attachments=None):
    """
    Send a plain text email via SMTP, optionally with file attachments.

    Args:
        subject: Email subject line
        recipients: List of recipient email addresses or single email string
        body: Plain text email body
        sender: Optional sender email (defaults to config's default_sender)
        config: Optional SmtpConfig (defaults to module-level config)
        attachments: Optional list of attachments. Each item can be:
            - A file path string (filename derived from path)
            - A (display_name, file_path) tuple

    Returns:
        bool: True if sent successfully, False otherwise
    """
    global _config

    cfg = config or _config
    if cfg is None:
        cfg = init_email()

    if not cfg.server or cfg.server == 'localhost':
        logging.warning("Email not configured - skipping send")
        return False

    # Normalize recipients
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in recipients if r and r.strip()]

    if not recipients:
        logging.warning("No valid recipients - skipping email")
        return False

    sender = sender or cfg.default_sender

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if attachments:
            for attachment in attachments:
                if isinstance(attachment, str):
                    file_path = attachment
                    filename = os.path.basename(file_path)
                elif isinstance(attachment, tuple) and len(attachment) == 2:
                    filename, file_path = attachment
                else:
                    continue

                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                maintype, subtype = mime_type.split('/', 1)

                with open(file_path, 'rb') as f:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition', 'attachment', filename=filename)
                msg.attach(part)

        if cfg.use_tls:
            server = smtplib.SMTP(cfg.server, cfg.port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(cfg.server, cfg.port)

        if cfg.username and cfg.password:
            server.login(cfg.username, cfg.password)

        server.sendmail(sender, recipients, msg.as_string())
        server.quit()

        logging.info(
            f"Email sent: {subject} to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False
