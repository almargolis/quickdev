# Background Jobs Idiom Example

This example demonstrates a simple job queue pattern that could be packaged as a QuickDev idiom.

## The Problem

Web requests should be fast (<200ms). Long-running tasks cause timeouts:
- Sending emails
- Processing images
- Generating reports
- API calls to slow services
- Data imports/exports

Traditional solutions (Celery, RQ) are powerful but complex for simple cases.

## The Idiom Pattern

A lightweight, database-backed job queue:

```python
from qdjobs import JobQueue

queue = JobQueue(app)

# Register tasks with decorator
@queue.task('send_email')
def send_email(to, subject, body):
    # Long-running task
    return {'sent': True}

# Enqueue from your routes
@app.route('/send-welcome')
def send_welcome():
    queue.enqueue('send_email',
        to='user@example.com',
        subject='Welcome!',
        body='...')
    return 'Email queued!'
```

## Running the Example

```bash
python job_queue.py

# In another terminal, enqueue jobs:
curl -X POST http://localhost:5004/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "send_email",
    "params": {
      "to": "user@example.com",
      "subject": "Test",
      "body": "Hello World"
    }
  }'

# Check job status
curl http://localhost:5004/jobs/1

# List all jobs
curl http://localhost:5004/jobs
```

## How It Works

### 1. Job Model

Tracks job state in database:

```python
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100))
    params = db.Column(db.Text)  # JSON
    status = db.Column(db.String(20))  # pending/running/completed/failed
    result = db.Column(db.Text)  # JSON
    error = db.Column(db.Text)
    # timestamps...
```

### 2. Task Registry

Decorator to register tasks:

```python
@queue.task('send_email')
def send_email(to, subject, body):
    # Your logic here
    return result
```

### 3. Background Worker

Thread that processes jobs:

```python
while running:
    job = Job.query.filter_by(status='pending').first()
    if job:
        process_job(job)
    else:
        sleep(1)
```

### 4. Simple API

Enqueue and check status:

```python
# Enqueue
job = queue.enqueue('send_email', to='...', subject='...')

# Check status
job.status  # pending/running/completed/failed
job.result  # Result data
job.error   # Error message if failed
```

## Registered Tasks

The example includes three tasks:

### send_email
```python
@queue.task('send_email')
def send_email(to, subject, body):
    # Simulate email sending
    time.sleep(2)
    return {'sent': True, 'to': to}
```

### process_image
```python
@queue.task('process_image')
def process_image(image_path, operations):
    # Simulate image processing
    time.sleep(3)
    return {'processed': True, 'path': image_path}
```

### generate_report
```python
@queue.task('generate_report')
def generate_report(report_type, params):
    # Simulate report generation
    time.sleep(5)
    return {'report_url': f'/reports/{report_type}.pdf'}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /jobs | Create a job |
| GET | /jobs | List all jobs |
| GET | /jobs?status=completed | Filter by status |
| GET | /jobs/:id | Get job details |

## Real-World Usage

### Email Sending

```python
@app.route('/register', methods=['POST'])
def register():
    user = create_user(request.form)

    # Queue welcome email (don't block response)
    queue.enqueue('send_email',
        to=user.email,
        subject='Welcome!',
        body=render_template('welcome_email.html', user=user))

    return 'Registration complete! Check your email.'
```

### Image Processing

```python
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    path = save_file(file)

    # Queue thumbnail generation
    queue.enqueue('process_image',
        image_path=path,
        operations=['resize:200x200', 'optimize'])

    return {'uploaded': True, 'processing': True}
```

### Report Generation

```python
@app.route('/reports/<report_type>')
def request_report(report_type):
    job = queue.enqueue('generate_report',
        report_type=report_type,
        params=request.args)

    return {
        'job_id': job.id,
        'status_url': f'/jobs/{job.id}'
    }
```

## Advantages

**vs. Celery/RQ:**
- No Redis/RabbitMQ dependency
- Simpler setup (SQLite-backed)
- Good for low-volume apps
- Easier to understand/debug

**vs. No queue:**
- Non-blocking web responses
- Retry failed jobs
- Track job history
- Monitor progress

## Limitations

This is a **simple** idiom for **simple** needs:
- ✓ Low-medium volume (<1000 jobs/day)
- ✓ Single server
- ✓ Simple retry logic
- ✗ High volume
- ✗ Distributed workers
- ✗ Complex workflows
- ✗ Job priorities

For complex needs, use Celery/RQ. But for many apps, this idiom is enough.

## Packaging as an Idiom

This pattern could be packaged as `qdjobs`:

```python
from qdjobs import init_job_queue

# One line setup
queue = init_job_queue(app, db)

# Register tasks
@queue.task('send_email')
def send_email(**params):
    pass

# Use it
queue.enqueue('send_email', ...)
```

Install across projects:
```bash
pip install qdjobs
```

## Extending the Pattern

### Add Job Retries

```python
job.retry_count = db.Column(db.Integer, default=0)
job.max_retries = db.Column(db.Integer, default=3)

# In worker
if job.status == 'failed' and job.retry_count < job.max_retries:
    job.status = 'pending'
    job.retry_count += 1
    db.session.commit()
```

### Add Job Scheduling

```python
job.scheduled_at = db.Column(db.DateTime)

# In worker
job = Job.query.filter(
    Job.status == 'pending',
    Job.scheduled_at <= datetime.utcnow()
).first()
```

### Add Job Priorities

```python
job.priority = db.Column(db.Integer, default=0)

# In worker
job = Job.query.filter_by(status='pending')
    .order_by(Job.priority.desc(), Job.created_at)
    .first()
```

## The Idiom Philosophy

This example shows QuickDev's approach:
1. **Identify common pattern** (background jobs)
2. **Extract the essence** (task registry + worker + DB)
3. **Make it reusable** (decorator + simple API)
4. **Package it** (install once, use everywhere)

You've probably written this code 5 times. Make it an idiom, write it once.

## Next Steps

1. Try the example
2. Add your own tasks
3. Consider: what tasks do YOU queue repeatedly?
4. Package your pattern as an idiom
5. Share across your projects

QuickDev is about capturing YOUR patterns.
