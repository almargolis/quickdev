"""
Email Sending Idiom - QuickDev Pattern

Template-based email sending with common patterns.
This demonstrates how to package repetitive email code as an idiom.

Could be packaged as: from qdemail import EmailManager
"""

from flask import Flask, render_template_string
from dataclasses import dataclass
from typing import Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@dataclass
class EmailConfig:
    """Email configuration."""
    smtp_host: str = 'localhost'
    smtp_port: int = 1025  # MailHog default
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = 'noreply@example.com'
    from_name: str = 'Example App'
    use_tls: bool = False


class EmailTemplate:
    """Base class for email templates."""

    subject = "Email Subject"
    template = "Email body"

    def __init__(self, **context):
        self.context = context

    def render_subject(self):
        """Render subject with context."""
        return render_template_string(self.subject, **self.context)

    def render_body(self):
        """Render body with context."""
        return render_template_string(self.template, **self.context)

    def get_recipients(self):
        """Get recipient email addresses."""
        return [self.context.get('to')]


class WelcomeEmail(EmailTemplate):
    """Welcome email template."""

    subject = "Welcome to {{ app_name }}!"

    template = """
    <h1>Welcome {{ user_name }}!</h1>

    <p>Thanks for joining {{ app_name }}. We're excited to have you!</p>

    <p>Here's what you can do next:</p>
    <ul>
        <li>Complete your profile</li>
        <li>Explore our features</li>
        <li>Invite your team</li>
    </ul>

    <p>If you have any questions, just reply to this email.</p>

    <p>Best regards,<br>
    The {{ app_name }} Team</p>
    """


class PasswordResetEmail(EmailTemplate):
    """Password reset email template."""

    subject = "Reset your password"

    template = """
    <h1>Password Reset Request</h1>

    <p>Hi {{ user_name }},</p>

    <p>We received a request to reset your password. Click the link below to choose a new password:</p>

    <p><a href="{{ reset_url }}">Reset Password</a></p>

    <p>This link expires in {{ expiry_hours }} hours.</p>

    <p>If you didn't request this, you can safely ignore this email.</p>

    <p>Best regards,<br>
    The {{ app_name }} Team</p>
    """


class NotificationEmail(EmailTemplate):
    """Generic notification email."""

    subject = "{{ title }}"

    template = """
    <h1>{{ title }}</h1>

    <p>{{ message }}</p>

    {% if action_url %}
    <p><a href="{{ action_url }}">{{ action_text or 'View Details' }}</a></p>
    {% endif %}

    <p>Best regards,<br>
    The {{ app_name }} Team</p>
    """


class InvoiceEmail(EmailTemplate):
    """Invoice email template."""

    subject = "Invoice #{{ invoice_number }} - ${{ amount }}"

    template = """
    <h1>Invoice #{{ invoice_number }}</h1>

    <p>Hi {{ customer_name }},</p>

    <p>Thanks for your payment of ${{ amount }}.</p>

    <h2>Details:</h2>
    <ul>
        <li><strong>Invoice:</strong> #{{ invoice_number }}</li>
        <li><strong>Date:</strong> {{ date }}</li>
        <li><strong>Amount:</strong> ${{ amount }}</li>
        <li><strong>Status:</strong> {{ status }}</li>
    </ul>

    <p><a href="{{ invoice_url }}">View Invoice</a></p>

    <p>Questions? Contact us at support@example.com</p>

    <p>Best regards,<br>
    The {{ app_name }} Team</p>
    """


class EmailManager:
    """
    Email manager with template support.

    Usage:
        email = EmailManager(app)

        # Send using template
        email.send(WelcomeEmail(
            to='user@example.com',
            user_name='John',
            app_name='MyApp'
        ))

        # Send simple email
        email.send_simple(
            to='user@example.com',
            subject='Hello',
            body='<p>Welcome!</p>'
        )
    """

    def __init__(self, app=None, config=None):
        self.config = config or EmailConfig()
        self.templates = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app."""
        # Load config from app if present
        self.config.smtp_host = app.config.get('SMTP_HOST', self.config.smtp_host)
        self.config.smtp_port = app.config.get('SMTP_PORT', self.config.smtp_port)
        self.config.smtp_user = app.config.get('SMTP_USER', self.config.smtp_user)
        self.config.smtp_password = app.config.get('SMTP_PASSWORD', self.config.smtp_password)
        self.config.from_email = app.config.get('FROM_EMAIL', self.config.from_email)
        self.config.from_name = app.config.get('FROM_NAME', self.config.from_name)

    def send(self, template: EmailTemplate):
        """Send email using a template."""
        subject = template.render_subject()
        body = template.render_body()
        recipients = template.get_recipients()

        return self._send_email(recipients, subject, body)

    def send_simple(self, to: str, subject: str, body: str, cc: Optional[List[str]] = None):
        """Send a simple email without a template."""
        recipients = [to] + (cc or [])
        return self._send_email(recipients, subject, body)

    def send_bulk(self, template_class, recipients_data: List[dict]):
        """Send the same template to multiple recipients with different data."""
        results = []
        for data in recipients_data:
            template = template_class(**data)
            result = self.send(template)
            results.append(result)
        return results

    def _send_email(self, to: List[str], subject: str, body: str):
        """Internal method to send email via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = ', '.join(to)

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()

                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)

                server.send_message(msg)

            return {'sent': True, 'to': to}

        except Exception as e:
            print(f"Email sending failed: {e}")
            return {'sent': False, 'error': str(e)}


# Example Flask app
if __name__ == '__main__':
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    # For local testing, use MailHog: docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
    app.config['SMTP_HOST'] = 'localhost'
    app.config['SMTP_PORT'] = 1025
    app.config['FROM_EMAIL'] = 'noreply@example.com'
    app.config['FROM_NAME'] = 'Example App'

    email_manager = EmailManager(app)

    @app.route('/send/welcome', methods=['POST'])
    def send_welcome():
        """Send a welcome email."""
        data = request.get_json()

        email = WelcomeEmail(
            to=data['to'],
            user_name=data.get('user_name', 'there'),
            app_name=data.get('app_name', 'Our App')
        )

        result = email_manager.send(email)
        return jsonify(result)

    @app.route('/send/password-reset', methods=['POST'])
    def send_password_reset():
        """Send a password reset email."""
        data = request.get_json()

        email = PasswordResetEmail(
            to=data['to'],
            user_name=data.get('user_name'),
            reset_url=data['reset_url'],
            expiry_hours=data.get('expiry_hours', 24),
            app_name=data.get('app_name', 'Our App')
        )

        result = email_manager.send(email)
        return jsonify(result)

    @app.route('/send/notification', methods=['POST'])
    def send_notification():
        """Send a notification email."""
        data = request.get_json()

        email = NotificationEmail(
            to=data['to'],
            title=data['title'],
            message=data['message'],
            action_url=data.get('action_url'),
            action_text=data.get('action_text'),
            app_name=data.get('app_name', 'Our App')
        )

        result = email_manager.send(email)
        return jsonify(result)

    @app.route('/send/invoice', methods=['POST'])
    def send_invoice():
        """Send an invoice email."""
        data = request.get_json()

        email = InvoiceEmail(**data)
        result = email_manager.send(email)
        return jsonify(result)

    @app.route('/')
    def index():
        return """
        <h1>Email Patterns Example</h1>
        <h2>Available Email Templates:</h2>
        <ul>
            <li><strong>WelcomeEmail</strong> - Welcome new users</li>
            <li><strong>PasswordResetEmail</strong> - Password reset links</li>
            <li><strong>NotificationEmail</strong> - Generic notifications</li>
            <li><strong>InvoiceEmail</strong> - Send invoices</li>
        </ul>
        <h2>API Endpoints:</h2>
        <ul>
            <li>POST /send/welcome</li>
            <li>POST /send/password-reset</li>
            <li>POST /send/notification</li>
            <li>POST /send/invoice</li>
        </ul>
        <h3>Try it (requires MailHog):</h3>
        <pre>
# Start MailHog: docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
# View emails: http://localhost:8025

# Send welcome email
curl -X POST http://localhost:5005/send/welcome \\
  -H "Content-Type: application/json" \\
  -d '{"to": "user@example.com", "user_name": "John", "app_name": "MyApp"}'

# Send password reset
curl -X POST http://localhost:5005/send/password-reset \\
  -H "Content-Type: application/json" \\
  -d '{"to": "user@example.com", "user_name": "John", "reset_url": "https://example.com/reset/token123"}'

# Send notification
curl -X POST http://localhost:5005/send/notification \\
  -H "Content-Type: application/json" \\
  -d '{"to": "user@example.com", "title": "New Comment", "message": "Someone commented on your post"}'
        </pre>
        """

    app.run(debug=True, port=5005)
