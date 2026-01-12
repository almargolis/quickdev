#!/usr/bin/env python3
"""
Quick email configuration test script for qdflask.

Usage:
    python qdflask/test_email.py recipient@example.com
"""

import sys
import os
from pathlib import Path
from flask import Flask
from qdflask.mail_utils import init_mail, send_email

def test_email_config(recipient):
    """Test email configuration by sending a test message."""

    # Create minimal Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'

    print("=" * 60)
    print("qdflask Email Configuration Test")
    print("=" * 60)

    # Check for email.yaml
    email_yaml_path = Path('conf/email.yaml')
    if email_yaml_path.exists():
        print(f"✓ Found: {email_yaml_path}")
    else:
        print(f"✗ Missing: {email_yaml_path}")
        print("  Copy qdflask/conf/email.yaml.example to conf/email.yaml")
        return False

    # Check for SMTP_PW
    smtp_pw = os.environ.get('SMTP_PW')
    if smtp_pw:
        print(f"✓ SMTP_PW environment variable set ({len(smtp_pw)} chars)")
    else:
        # Try backwards compatibility
        smtp_pw = os.environ.get('MAIL_PASSWORD') or os.environ.get('SENDGRID_API_KEY')
        if smtp_pw:
            print(f"⚠ Using legacy env var ({len(smtp_pw)} chars)")
            print("  Consider updating to SMTP_PW in .env")
        else:
            print("✗ SMTP_PW not set in environment")
            print("  Add SMTP_PW=your-password to .env")
            return False

    print()
    print("Initializing Flask-Mail...")

    try:
        with app.app_context():
            init_mail(app)

            # Display loaded configuration
            print(f"  Server: {app.config.get('MAIL_SERVER')}")
            print(f"  Port: {app.config.get('MAIL_PORT')}")
            print(f"  TLS: {app.config.get('MAIL_USE_TLS')}")
            print(f"  Username: {app.config.get('MAIL_USERNAME')}")
            print(f"  Sender: {app.config.get('MAIL_DEFAULT_SENDER')}")
            print()

            # Send test email
            print(f"Sending test email to {recipient}...")

            success = send_email(
                subject="qdflask Email Test",
                recipients=[recipient],
                body="""This is a test email from qdflask.

If you received this, your email configuration is working correctly!

Configuration details:
- SMTP Server: {server}
- Using: conf/email.yaml + SMTP_PW from .env

--
Sent by qdflask test_email.py
""".format(server=app.config.get('MAIL_SERVER'))
            )

            if success:
                print("✓ Email sent successfully!")
                print(f"  Check {recipient} for the test message")
                return True
            else:
                print("✗ Failed to send email")
                print("  Check the error messages above")
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python qdflask/test_email.py recipient@example.com")
        print()
        print("Example:")
        print("  python qdflask/test_email.py youremail@gmail.com")
        sys.exit(1)

    recipient = sys.argv[1]

    # Load .env if it exists
    env_path = Path('conf/.env')
    if env_path.exists():
        print(f"Loading environment from {env_path}")
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print()

    success = test_email_config(recipient)
    sys.exit(0 if success else 1)
