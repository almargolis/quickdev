#!/bin/bash
#
# QuickDev Examples - Quick Start Script
#
# This script helps you quickly set up and try the QuickDev examples.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}QuickDev Examples - Quick Start${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored status messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the examples directory
if [ ! -f "quickstart.sh" ]; then
    error "Please run this script from the examples/ directory"
    exit 1
fi

# Check Python version
info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
info "Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    python3 -m venv venv
    success "Virtual environment created"
else
    info "Virtual environment already exists"
fi

# Activate virtual environment
info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
info "Installing dependencies..."
pip install flask flask-sqlalchemy flask-login werkzeug > /dev/null 2>&1
success "Dependencies installed"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Interactive menu
while true; do
    echo "Which example would you like to run?"
    echo ""
    echo "  1) Before/After Comparison (⭐ START HERE)"
    echo "  2) Flask Integration"
    echo "  3) XSynth Tutorial"
    echo "  4) CRUD API"
    echo "  5) Background Jobs"
    echo "  6) Email Patterns"
    echo "  7) Run all examples (in separate terminals)"
    echo "  8) Exit"
    echo ""
    read -p "Enter your choice (1-8): " choice

    case $choice in
        1)
            echo ""
            info "Starting Before/After Comparison..."
            echo ""
            echo -e "${YELLOW}This will start TWO servers:${NC}"
            echo -e "  ${BLUE}Traditional:${NC} http://localhost:5001"
            echo -e "  ${BLUE}QuickDev:${NC}    http://localhost:5002"
            echo ""
            echo "Press Ctrl+C to stop"
            echo ""
            sleep 2

            # Start both servers
            cd before-after
            python before_manual.py &
            PID1=$!
            python after_quickdev.py &
            PID2=$!

            # Wait for Ctrl+C
            trap "kill $PID1 $PID2; exit" INT
            wait

            ;;

        2)
            echo ""
            info "Starting Flask Integration example..."
            echo ""
            warning "Note: This example requires qdflask and qdimages to be installed"
            echo "Run: pip install -e ../qdflask ../qdimages"
            echo ""
            echo "Server will be at: http://localhost:5000"
            echo "Press Ctrl+C to stop"
            echo ""
            sleep 2

            cd flask-integration
            python app.py
            ;;

        3)
            echo ""
            info "XSynth Tutorial"
            echo ""
            echo "The XSynth tutorial shows code generation."
            echo ""
            echo "Files to examine:"
            echo -e "  ${BLUE}user_model.xpy${NC} - Source with XSynth directives"
            echo -e "  ${BLUE}user_model.py${NC}  - Generated Python output"
            echo ""
            echo "To regenerate:"
            echo -e "  ${YELLOW}cd xsynth-tutorial${NC}"
            echo -e "  ${YELLOW}python ../../qdutils/xsynth.py .${NC}"
            echo ""
            read -p "Press Enter to continue..."
            ;;

        4)
            echo ""
            info "Starting CRUD API example..."
            echo ""
            echo "Server will be at: http://localhost:5003"
            echo ""
            echo "Try these commands:"
            echo -e "  ${YELLOW}# Seed database${NC}"
            echo "  flask seed"
            echo ""
            echo -e "  ${YELLOW}# Create a product${NC}"
            echo "  curl -X POST http://localhost:5003/api/products \\"
            echo "    -H 'Content-Type: application/json' \\"
            echo "    -d '{\"name\":\"Laptop\",\"price\":999.99}'"
            echo ""
            echo "Press Ctrl+C to stop"
            echo ""
            sleep 2

            cd crud-api
            python api.py
            ;;

        5)
            echo ""
            info "Starting Background Jobs example..."
            echo ""
            echo "Server will be at: http://localhost:5004"
            echo ""
            echo "Try enqueuing a job:"
            echo -e "  ${YELLOW}curl -X POST http://localhost:5004/jobs \\${NC}"
            echo -e "    ${YELLOW}-H 'Content-Type: application/json' \\${NC}"
            echo -e "    ${YELLOW}-d '{\"task\":\"send_email\",\"params\":{\"to\":\"user@example.com\"}}' ${NC}"
            echo ""
            echo "Press Ctrl+C to stop"
            echo ""
            sleep 2

            cd background-jobs
            python job_queue.py
            ;;

        6)
            echo ""
            info "Starting Email Patterns example..."
            echo ""
            warning "For local testing, start MailHog first:"
            echo "  docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog"
            echo ""
            echo "View emails at: http://localhost:8025"
            echo "Server will be at: http://localhost:5005"
            echo ""
            echo "Press Ctrl+C to stop"
            echo ""
            sleep 2

            cd email-patterns
            python email_manager.py
            ;;

        7)
            echo ""
            info "This will open multiple terminal windows"
            warning "Make sure you have 'gnome-terminal', 'xterm', or macOS Terminal"
            echo ""
            read -p "Continue? (y/n): " confirm
            if [ "$confirm" = "y" ]; then
                # Detect OS and open terminals accordingly
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    # macOS
                    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)'/before-after && source ../venv/bin/activate && python before_manual.py"'
                    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)'/crud-api && source ../venv/bin/activate && python api.py"'
                    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)'/background-jobs && source ../venv/bin/activate && python job_queue.py"'
                elif command -v gnome-terminal &> /dev/null; then
                    # Linux with GNOME
                    gnome-terminal -- bash -c "cd before-after && source ../venv/bin/activate && python before_manual.py; exec bash"
                    gnome-terminal -- bash -c "cd crud-api && source ../venv/bin/activate && python api.py; exec bash"
                    gnome-terminal -- bash -c "cd background-jobs && source ../venv/bin/activate && python job_queue.py; exec bash"
                else
                    warning "Automatic terminal launching not supported on this system"
                    echo "Please open terminals manually and run the examples"
                fi
                success "Terminals launched!"
            fi
            ;;

        8)
            echo ""
            info "Thanks for trying QuickDev examples!"
            echo ""
            echo "Next steps:"
            echo "  - Read the README files in each example"
            echo "  - Try integrating qdflask/qdimages in your project"
            echo "  - Create your own idioms for common patterns"
            echo ""
            exit 0
            ;;

        *)
            error "Invalid choice. Please enter 1-8"
            ;;
    esac

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo ""
done
