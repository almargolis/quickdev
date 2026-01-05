#!/bin/bash
# publish-package.sh - Publish a single package from the monorepo to PyPI
#
# Usage:
#   ./scripts/publish-package.sh qdbase
#   ./scripts/publish-package.sh qdflask --test  # publish to TestPyPI
#   ./scripts/publish-package.sh xsynth --prod   # publish to production PyPI

set -e  # Exit on error

# Activate virtual environment if it exists
if [ -f "ezdev.venv/bin/activate" ]; then
    source ezdev.venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

PACKAGE=$1
MODE=${2:-test}  # Default to test mode

if [ -z "$PACKAGE" ]; then
    echo "Usage: $0 <package-name> [--test|--prod]"
    echo ""
    echo "Available packages:"
    echo "  qdbase    - Foundation utilities"
    echo "  xsynth    - Preprocessor"
    echo "  qdflask   - Flask authentication"
    echo "  qdimages  - Flask image management"
    echo "  qdcomments - Flask commenting system"
    exit 1
fi

# Check if package directory exists
if [ ! -d "$PACKAGE" ]; then
    echo "Error: Package directory '$PACKAGE' not found"
    exit 1
fi

# Check if setup.py exists
if [ ! -f "$PACKAGE/setup.py" ]; then
    echo "Error: setup.py not found in '$PACKAGE/'"
    exit 1
fi

echo "========================================="
echo "Publishing: $PACKAGE"
echo "Mode: $MODE"
echo "========================================="

# Navigate to package directory
cd "$PACKAGE"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Build the package
echo "Building package..."
if command -v python3 -m build &> /dev/null; then
    python3 -m build
else
    python3 setup.py sdist bdist_wheel
fi

# Upload based on mode
if [ "$MODE" == "--prod" ] || [ "$MODE" == "prod" ]; then
    echo "Uploading to PyPI (production)..."
    python3 -m twine upload dist/*
elif [ "$MODE" == "--test" ] || [ "$MODE" == "test" ]; then
    echo "Uploading to TestPyPI..."
    python3 -m twine upload --repository testpypi dist/*
else
    echo "Error: Invalid mode '$MODE'. Use --test or --prod"
    exit 1
fi

echo "========================================="
echo "Successfully published $PACKAGE!"
echo "========================================="

# Navigate back
cd ..
