#!/bin/bash
# build-all.sh - Build all packages in the monorepo
#
# This script builds distribution packages for all QuickDev packages
# without publishing them. Useful for testing before release.

set -e  # Exit on error

# Activate virtual environment if it exists
if [ -f "ezdev.venv/bin/activate" ]; then
    source ezdev.venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

PACKAGES="qdbase xsynth qdflask qdimages qdcomments"

echo "========================================="
echo "Building all QuickDev packages"
echo "========================================="

for PACKAGE in $PACKAGES; do
    if [ -d "$PACKAGE" ] && [ -f "$PACKAGE/setup.py" ]; then
        echo ""
        echo "Building $PACKAGE..."
        cd "$PACKAGE"

        # Clean previous builds
        rm -rf build/ dist/ *.egg-info

        # Build using modern build tool (or fallback to setup.py)
        if command -v python3 -m build &> /dev/null; then
            python3 -m build
        else
            python3 setup.py sdist bdist_wheel
        fi

        echo "✓ Built $PACKAGE"
        cd ..
    else
        echo "⊘ Skipping $PACKAGE (directory or setup.py not found)"
    fi
done

echo ""
echo "========================================="
echo "Build complete!"
echo "========================================="
echo ""
echo "Distribution files created in each package's dist/ directory"
echo ""
echo "To publish a package:"
echo "  ./scripts/publish-package.sh <package-name> --test   # TestPyPI"
echo "  ./scripts/publish-package.sh <package-name> --prod   # Production PyPI"
