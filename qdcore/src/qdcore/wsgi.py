"""
qdcore.wsgi - WSGI file generation for Flask applications

Provides utilities to generate WSGI configuration files for deploying
Flask applications with Apache mod_wsgi or other WSGI servers.
"""

import os


def compose_wsgi_file(site_root, filename="flask.wsgi"):
    """
    Create a WSGI file for Flask application deployment.

    Writes a flask.wsgi file to the site root directory that can be
    used by Apache mod_wsgi or other WSGI servers.

    Args:
        site_root: Path to the site root directory
        filename: Name of the WSGI file (default: flask.wsgi)

    Returns:
        Path to the created WSGI file

    Example:
        compose_wsgi_file('/var/www/mysite')
        # Creates /var/www/mysite/flask.wsgi
    """
    # TODO: Replace hardcoded values with qdconf variables
    # TODO: Add conditional logic for different configurations
    wsgi_content = '''#!/usr/bin/python3
import sys
import os

# Add your project directory
project_home = '/var/www/tmih_flask'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import Flask app
from app import create_app
application = create_app()
'''

    wsgi_path = os.path.join(site_root, filename)
    with open(wsgi_path, 'w', encoding='utf-8') as f:
        f.write(wsgi_content)

    # Make executable
    os.chmod(wsgi_path, 0o755)

    return wsgi_path
