# Email Patterns Idiom Example

This example demonstrates template-based email sending as a reusable idiom.

## The Email Problem

Every app sends the same emails:
- Welcome emails
- Password resets
- Notifications
- Invoices
- Receipts
- Reminders

You end up rewriting the same templates and sending logic repeatedly.

## The Idiom Pattern

Template-based emails with consistent structure:

```python
from qdemail import EmailManager, WelcomeEmail

email = EmailManager(app)

# Send using template
email.send(WelcomeEmail(
    to='user@example.com',
    user_name='John',
    app_name='MyApp'
))
```

## Running the Example

### Prerequisites

For local testing, run MailHog to catch emails:

```bash
docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

Then view emails at: http://localhost:8025

### Run the App

```bash
python email_manager.py

# Send a welcome email
curl -X POST http://localhost:5005/send/welcome \
  -H "Content-Type: application/json" \
  -d '{"to": "user@example.com", "user_name": "John", "app_name": "MyApp"}'

# Check MailHog UI to see the email
```

## Included Email Templates

### WelcomeEmail

Welcome new users with a friendly onboarding email.

```python
email.send(WelcomeEmail(
    to='user@example.com',
    user_name='John Doe',
    app_name='MyApp'
))
```

### PasswordResetEmail

Send password reset links.

```python
email.send(PasswordResetEmail(
    to='user@example.com',
    user_name='John',
    reset_url='https://example.com/reset/abc123',
    expiry_hours=24,
    app_name='MyApp'
))
```

### NotificationEmail

Generic notifications for various events.

```python
email.send(NotificationEmail(
    to='user@example.com',
    title='New Comment',
    message='Someone commented on your post',
    action_url='https://example.com/posts/123',
    action_text='View Comment',
    app_name='MyApp'
))
```

### InvoiceEmail

Send invoices and receipts.

```python
email.send(InvoiceEmail(
    to='customer@example.com',
    customer_name='ACME Corp',
    invoice_number='INV-001',
    date='2025-01-15',
    amount='499.99',
    status='Paid',
    invoice_url='https://example.com/invoices/001',
    app_name='MyApp'
))
```

## Creating Custom Templates

Extend `EmailTemplate` for your needs:

```python
class OrderConfirmationEmail(EmailTemplate):
    subject = "Order #{{ order_number }} Confirmed"

    template = """
    <h1>Order Confirmed!</h1>

    <p>Hi {{ customer_name }},</p>

    <p>Your order #{{ order_number }} has been confirmed.</p>

    <h2>Items:</h2>
    <ul>
    {% for item in items %}
        <li>{{ item.name }} - ${{ item.price }}</li>
    {% endfor %}
    </ul>

    <p><strong>Total:</strong> ${{ total }}</p>

    <p><a href="{{ order_url }}">Track Your Order</a></p>
    """
```

Then use it:

```python
email.send(OrderConfirmationEmail(
    to='customer@example.com',
    customer_name='John',
    order_number='12345',
    items=[
        {'name': 'Widget', 'price': 29.99},
        {'name': 'Gadget', 'price': 49.99}
    ],
    total=79.98,
    order_url='https://example.com/orders/12345'
))
```

## Integration Patterns

### With User Registration

```python
@app.route('/register', methods=['POST'])
def register():
    user = create_user(request.form)

    # Send welcome email
    email_manager.send(WelcomeEmail(
        to=user.email,
        user_name=user.name,
        app_name='MyApp'
    ))

    return 'Registration complete!'
```

### With Password Reset

```python
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    user = User.query.filter_by(email=request.form['email']).first()
    reset_token = generate_reset_token(user)

    email_manager.send(PasswordResetEmail(
        to=user.email,
        user_name=user.name,
        reset_url=url_for('reset_password', token=reset_token, _external=True),
        expiry_hours=24,
        app_name='MyApp'
    ))

    return 'Reset link sent!'
```

### With Background Jobs

Combine with the job queue idiom for async sending:

```python
@queue.task('send_email')
def send_email_task(template_class, **context):
    template = globals()[template_class](**context)
    return email_manager.send(template)

# Enqueue email
queue.enqueue('send_email',
    template_class='WelcomeEmail',
    to='user@example.com',
    user_name='John',
    app_name='MyApp'
)
```

## Bulk Sending

Send the same template to multiple recipients:

```python
recipients = [
    {'to': 'user1@example.com', 'user_name': 'Alice', 'app_name': 'MyApp'},
    {'to': 'user2@example.com', 'user_name': 'Bob', 'app_name': 'MyApp'},
    {'to': 'user3@example.com', 'user_name': 'Charlie', 'app_name': 'MyApp'},
]

results = email_manager.send_bulk(WelcomeEmail, recipients)
```

## Configuration

Configure via Flask app config:

```python
app.config['SMTP_HOST'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USER'] = 'your-email@gmail.com'
app.config['SMTP_PASSWORD'] = 'your-app-password'
app.config['FROM_EMAIL'] = 'noreply@yourapp.com'
app.config['FROM_NAME'] = 'Your App Name'
app.config['SMTP_USE_TLS'] = True

email_manager = EmailManager(app)
```

Or pass config directly:

```python
from email_manager import EmailConfig

config = EmailConfig(
    smtp_host='smtp.sendgrid.net',
    smtp_port=587,
    smtp_user='apikey',
    smtp_password='your-sendgrid-api-key',
    from_email='noreply@yourapp.com',
    from_name='Your App',
    use_tls=True
)

email_manager = EmailManager(config=config)
```

## Common Email Providers

### Gmail

```python
app.config['SMTP_HOST'] = 'smtp.gmail.com'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USE_TLS'] = True
# Use App Password, not regular password
```

### SendGrid

```python
app.config['SMTP_HOST'] = 'smtp.sendgrid.net'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USER'] = 'apikey'
app.config['SMTP_PASSWORD'] = 'your-sendgrid-api-key'
app.config['SMTP_USE_TLS'] = True
```

### Mailgun

```python
app.config['SMTP_HOST'] = 'smtp.mailgun.org'
app.config['SMTP_PORT'] = 587
app.config['SMTP_USER'] = 'postmaster@your-domain.mailgun.org'
app.config['SMTP_PASSWORD'] = 'your-smtp-password'
app.config['SMTP_USE_TLS'] = True
```

## Advantages

**vs. Hardcoded emails:**
- Reusable templates across projects
- Consistent styling
- Easy to update
- Type-safe (dataclasses)

**vs. Flask-Mail directly:**
- Higher-level abstraction
- Template management
- Common patterns built-in
- Easier testing

**vs. Third-party services:**
- No vendor lock-in
- Works with any SMTP
- Free for basic use
- Complete control

## Testing

Mock the email manager in tests:

```python
def test_registration_sends_welcome_email(mocker):
    mock_send = mocker.patch('email_manager.EmailManager.send')

    response = client.post('/register', data={
        'email': 'test@example.com',
        'name': 'Test User'
    })

    assert mock_send.called
    email_template = mock_send.call_args[0][0]
    assert isinstance(email_template, WelcomeEmail)
    assert email_template.context['user_name'] == 'Test User'
```

## Packaging as an Idiom

This pattern could be packaged as `qdemail`:

```python
from qdemail import (
    EmailManager,
    WelcomeEmail,
    PasswordResetEmail,
    NotificationEmail
)

email = EmailManager(app)
email.send(WelcomeEmail(to='...', user_name='...'))
```

Install once, use everywhere:
```bash
pip install qdemail
```

## The Idiom Philosophy

Email sending is a pattern you implement in every app:
- Same templates (welcome, reset, notification)
- Same SMTP configuration
- Same error handling
- Same testing patterns

QuickDev says: **Write it once, package it, reuse it.**

## Next Steps

1. Add your own email templates
2. Configure for your SMTP provider
3. Integrate with your app
4. Consider packaging as a reusable idiom
5. Share across your projects

Every app needs emails. Don't rewrite the same templates.
