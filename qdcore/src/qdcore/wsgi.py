"""
qdcore.wsgi - WSGI file generation for Flask applications

Provides utilities to generate WSGI configuration files for deploying
Flask applications with Apache mod_wsgi or other WSGI servers.
"""

import os
from qdbase import exenv


def compose_wsgi_file(filename="flask.wsgi", wsgi_path=None):
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
    if wsgi_path is None:
        wsgi_path = os.path.join(exenv.qdsite_dpath, filename)

    with open(wsgi_path, 'w', encoding='utf-8') as f:
        f.write("#!/usr/bin/python3\n")
        f.write("import sys\n")
        f.write("import os\n")
        f.write("\n")
        f.write("# Add your project directory\n")
        f.write("project_home = '/var/www/tmih_flask'\n")
        f.write("if project_home not in sys.path:\n")
        f.write("    sys.path.insert(0, project_home)\n")
        f.write("\n")
        f.write("# Load environment variables\n")
        f.write("from dotenv import load_dotenv\n")
        f.write("load_dotenv(os.path.join(project_home, '.env'))\n")
        f.write("\n")
        f.write("# Import Flask app\n")
        f.write("from app import create_app\n")
        f.write("application = create_app()\n")

    # Make executable
    os.chmod(wsgi_path, 0o755)

    return wsgi_path

def qdo_compose_wsgi_file():
    wsgi_path = compose_wsgi_file()
    print(f"File '{wsgi_path}' created.")