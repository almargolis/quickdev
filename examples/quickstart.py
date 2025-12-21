#!/usr/bin/env python3
"""
QuickDev Examples - Quick Start Script (Python version)

Cross-platform script to set up and run QuickDev examples.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

    @classmethod
    def disable(cls):
        """Disable colors (for Windows CMD)."""
        cls.BLUE = cls.GREEN = cls.YELLOW = cls.RED = cls.NC = ''


# Disable colors on Windows unless using Windows Terminal
if platform.system() == 'Windows' and not os.environ.get('WT_SESSION'):
    Colors.disable()


def info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")


def warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")


def error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


def run_command(cmd, cwd=None):
    """Run a shell command."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False


def setup_environment():
    """Set up virtual environment and install dependencies."""
    print(f"{Colors.BLUE}========================================{Colors.NC}")
    print(f"{Colors.BLUE}QuickDev Examples - Quick Start{Colors.NC}")
    print(f"{Colors.BLUE}========================================{Colors.NC}")
    print()

    # Check Python version
    info("Checking Python version...")
    version = sys.version.split()[0]
    info(f"Found Python {version}")

    # Create virtual environment
    venv_path = Path('venv')
    if not venv_path.exists():
        info("Creating virtual environment...")
        if not run_command(f"{sys.executable} -m venv venv"):
            error("Failed to create virtual environment")
            sys.exit(1)
        success("Virtual environment created")
    else:
        info("Virtual environment already exists")

    # Determine activation script
    if platform.system() == 'Windows':
        python_exe = 'venv\\Scripts\\python.exe'
        pip_exe = 'venv\\Scripts\\pip.exe'
    else:
        python_exe = 'venv/bin/python'
        pip_exe = 'venv/bin/pip'

    # Upgrade pip
    info("Upgrading pip...")
    run_command(f"{pip_exe} install --upgrade pip --quiet")

    # Install dependencies
    info("Installing dependencies...")
    deps = 'flask flask-sqlalchemy flask-login werkzeug'
    if not run_command(f"{pip_exe} install {deps} --quiet"):
        error("Failed to install dependencies")
        sys.exit(1)
    success("Dependencies installed")

    print()
    print(f"{Colors.GREEN}========================================{Colors.NC}")
    print(f"{Colors.GREEN}Setup Complete!{Colors.NC}")
    print(f"{Colors.GREEN}========================================{Colors.NC}")
    print()

    return python_exe


def show_menu():
    """Display the main menu."""
    print("Which example would you like to run?")
    print()
    print("  1) Before/After Comparison (⭐ START HERE)")
    print("  2) Flask Integration")
    print("  3) XSynth Tutorial")
    print("  4) CRUD API")
    print("  5) Background Jobs")
    print("  6) Email Patterns")
    print("  7) Exit")
    print()


def run_example(choice, python_exe):
    """Run the selected example."""
    if choice == '1':
        print()
        info("Before/After Comparison")
        print()
        print(f"{Colors.YELLOW}To compare:${Colors.NC}")
        print(f"  {Colors.BLUE}Traditional:{Colors.NC} cd before-after && {python_exe} before_manual.py")
        print(f"  {Colors.BLUE}QuickDev:{Colors.NC}    cd before-after && {python_exe} after_quickdev.py")
        print()
        print("The traditional version runs on http://localhost:5001")
        print("The QuickDev version runs on http://localhost:5002")
        print()
        choice = input("Run (t)raditional, (q)uickdev, or (b)oth? [t/q/b]: ").lower()

        if choice == 't':
            os.chdir('before-after')
            subprocess.run([f"../{python_exe}", "before_manual.py"])
        elif choice == 'q':
            os.chdir('before-after')
            subprocess.run([f"../{python_exe}", "after_quickdev.py"])
        elif choice == 'b':
            warning("Open two terminals and run each command separately")
            print()

    elif choice == '2':
        print()
        info("Flask Integration example")
        print()
        warning("Note: Requires qdflask and qdimages to be installed")
        print("Run: pip install -e ../qdflask ../qdimages")
        print()
        input("Press Enter to continue...")
        os.chdir('flask-integration')
        subprocess.run([f"../{python_exe}", "app.py"])

    elif choice == '3':
        print()
        info("XSynth Tutorial")
        print()
        print("The XSynth tutorial shows code generation.")
        print()
        print("Files to examine:")
        print(f"  {Colors.BLUE}user_model.xpy{Colors.NC} - Source with XSynth directives")
        print(f"  {Colors.BLUE}user_model.py{Colors.NC}  - Generated Python output")
        print()
        print("To regenerate:")
        print(f"  {Colors.YELLOW}cd xsynth-tutorial{Colors.NC}")
        print(f"  {Colors.YELLOW}python ../../qdutils/xsynth.py .{Colors.NC}")
        print()
        input("Press Enter to continue...")

    elif choice == '4':
        print()
        info("CRUD API example")
        print()
        print("Server will be at: http://localhost:5003")
        print()
        print("Try these commands:")
        print(f"  {Colors.YELLOW}# Create a product{Colors.NC}")
        print("  curl -X POST http://localhost:5003/api/products \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"name\":\"Laptop\",\"price\":999.99}'")
        print()
        input("Press Enter to start...")
        os.chdir('crud-api')
        subprocess.run([f"../{python_exe}", "api.py"])

    elif choice == '5':
        print()
        info("Background Jobs example")
        print()
        print("Server will be at: http://localhost:5004")
        print()
        input("Press Enter to start...")
        os.chdir('background-jobs')
        subprocess.run([f"../{python_exe}", "job_queue.py"])

    elif choice == '6':
        print()
        info("Email Patterns example")
        print()
        warning("For local testing, start MailHog first:")
        print("  docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog")
        print()
        print("View emails at: http://localhost:8025")
        print("Server will be at: http://localhost:5005")
        print()
        input("Press Enter to start...")
        os.chdir('email-patterns')
        subprocess.run([f"../{python_exe}", "email_manager.py"])

    elif choice == '7':
        print()
        info("Thanks for trying QuickDev examples!")
        print()
        print("Next steps:")
        print("  - Read the README files in each example")
        print("  - Try integrating qdflask/qdimages in your project")
        print("  - Create your own idioms for common patterns")
        print()
        sys.exit(0)

    else:
        error("Invalid choice")


def main():
    """Main entry point."""
    # Check if we're in the right directory
    if not Path('quickstart.py').exists():
        error("Please run this script from the examples/ directory")
        sys.exit(1)

    # Set up environment
    python_exe = setup_environment()

    # Main loop
    while True:
        show_menu()
        choice = input("Enter your choice (1-7): ")
        run_example(choice, python_exe)

        print()
        print(f"{Colors.BLUE}========================================{Colors.NC}")
        print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        info("Interrupted by user")
        sys.exit(0)
