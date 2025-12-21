"""
Background Jobs Idiom - QuickDev Pattern

A simple, database-backed job queue that demonstrates the idiom approach.
In production, use Celery/RQ, but for simple cases this pattern works well.

This could be packaged as: from qdjobs import init_job_queue
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
import json
import time
import threading


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


db = SQLAlchemy()


class Job(db.Model):
    """Background job model."""
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    task_name = db.Column(db.String(100), nullable=False)
    params = db.Column(db.Text)  # JSON
    status = db.Column(db.String(20), default=JobStatus.PENDING.value)
    result = db.Column(db.Text)  # JSON
    error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'task_name': self.task_name,
            'params': json.loads(self.params) if self.params else None,
            'status': self.status,
            'result': json.loads(self.result) if self.result else None,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self._calculate_duration(),
        }

    def _calculate_duration(self):
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None


class JobQueue:
    """
    Simple job queue manager.

    Usage:
        queue = JobQueue(app)

        @queue.task('send_email')
        def send_email(to, subject, body):
            # Send email logic
            return {'sent': True}

        # Enqueue a job
        queue.enqueue('send_email', to='user@example.com', ...)
    """

    def __init__(self, app=None):
        self.tasks = {}
        self.worker_thread = None
        self.running = False

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app."""
        db.init_app(app)
        self.app = app

    def task(self, name):
        """Decorator to register a task."""
        def decorator(func):
            self.tasks[name] = func
            return func
        return decorator

    def enqueue(self, task_name, name=None, **params):
        """Enqueue a job."""
        if task_name not in self.tasks:
            raise ValueError(f"Task not registered: {task_name}")

        job = Job(
            name=name or task_name,
            task_name=task_name,
            params=json.dumps(params),
            status=JobStatus.PENDING.value,
        )

        db.session.add(job)
        db.session.commit()

        return job

    def start_worker(self):
        """Start the background worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop_worker(self):
        """Stop the background worker."""
        self.running = False

    def _worker_loop(self):
        """Worker loop - processes pending jobs."""
        with self.app.app_context():
            while self.running:
                # Get next pending job
                job = Job.query.filter_by(
                    status=JobStatus.PENDING.value
                ).order_by(Job.created_at).first()

                if job:
                    self._process_job(job)
                else:
                    time.sleep(1)  # No jobs, wait a bit

    def _process_job(self, job):
        """Process a single job."""
        try:
            # Mark as running
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.utcnow()
            db.session.commit()

            # Get the task function
            task_func = self.tasks.get(job.task_name)
            if not task_func:
                raise ValueError(f"Task not found: {job.task_name}")

            # Execute the task
            params = json.loads(job.params) if job.params else {}
            result = task_func(**params)

            # Mark as completed
            job.status = JobStatus.COMPLETED.value
            job.result = json.dumps(result)
            job.completed_at = datetime.utcnow()
            db.session.commit()

        except Exception as e:
            # Mark as failed
            job.status = JobStatus.FAILED.value
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.session.commit()


# Example usage
if __name__ == '__main__':
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    queue = JobQueue(app)

    # Register tasks
    @queue.task('send_email')
    def send_email(to, subject, body):
        """Simulate sending an email."""
        print(f"Sending email to {to}: {subject}")
        time.sleep(2)  # Simulate work
        return {'sent': True, 'to': to}

    @queue.task('process_image')
    def process_image(image_path, operations):
        """Simulate image processing."""
        print(f"Processing {image_path} with {operations}")
        time.sleep(3)  # Simulate work
        return {'processed': True, 'path': image_path}

    @queue.task('generate_report')
    def generate_report(report_type, params):
        """Simulate report generation."""
        print(f"Generating {report_type} report")
        time.sleep(5)  # Simulate work
        return {'report_url': f'/reports/{report_type}.pdf'}

    # Routes
    from flask import jsonify, request

    @app.route('/jobs', methods=['POST'])
    def create_job():
        """Enqueue a job."""
        data = request.get_json()
        task_name = data.get('task')
        params = data.get('params', {})

        try:
            job = queue.enqueue(task_name, **params)
            return jsonify(job.to_dict()), 201
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/jobs', methods=['GET'])
    def list_jobs():
        """List all jobs."""
        status = request.args.get('status')
        query = Job.query

        if status:
            query = query.filter_by(status=status)

        jobs = query.order_by(Job.created_at.desc()).all()
        return jsonify([job.to_dict() for job in jobs])

    @app.route('/jobs/<int:job_id>', methods=['GET'])
    def get_job(job_id):
        """Get job status."""
        job = Job.query.get_or_404(job_id)
        return jsonify(job.to_dict())

    @app.route('/')
    def index():
        return """
        <h1>Background Jobs Example</h1>
        <h2>Available Tasks:</h2>
        <ul>
            <li>send_email - Simulate sending an email</li>
            <li>process_image - Simulate image processing</li>
            <li>generate_report - Simulate report generation</li>
        </ul>
        <h2>API Endpoints:</h2>
        <ul>
            <li>POST /jobs - Create a job</li>
            <li>GET /jobs - List all jobs</li>
            <li>GET /jobs?status=completed - Filter by status</li>
            <li>GET /jobs/:id - Get job status</li>
        </ul>
        <h3>Try it:</h3>
        <pre>
# Create a job
curl -X POST http://localhost:5004/jobs \\
  -H "Content-Type: application/json" \\
  -d '{"task": "send_email", "params": {"to": "user@example.com", "subject": "Test", "body": "Hello"}}'

# List jobs
curl http://localhost:5004/jobs

# Get job status
curl http://localhost:5004/jobs/1
        </pre>
        """

    # Start worker and run
    with app.app_context():
        db.create_all()
        queue.start_worker()

    app.run(debug=True, port=5004)
