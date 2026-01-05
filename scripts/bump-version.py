#!/usr/bin/env python3
"""
bump-version.py - Bump version numbers for QuickDev packages

Usage:
    python scripts/bump-version.py qdbase patch    # 0.2.0 -> 0.2.1
    python scripts/bump-version.py qdflask minor   # 0.1.0 -> 0.2.0
    python scripts/bump-version.py xsynth major    # 0.3.0 -> 1.0.0
    python scripts/bump-version.py all patch       # Bump all packages
"""

import re
import sys
from pathlib import Path


PACKAGES = ['qdbase', 'xsynth', 'qdflask', 'qdimages', 'qdcomments']


def parse_version(version_str):
    """Parse version string into (major, minor, patch) tuple."""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(version_str, bump_type):
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch = parse_version(version_str)

    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_setup_py(package_dir, new_version):
    """Update version in setup.py."""
    setup_path = package_dir / 'setup.py'
    if not setup_path.exists():
        print(f"  ⊘ No setup.py found in {package_dir}")
        return False

    content = setup_path.read_text()

    # Match version="X.Y.Z" pattern
    pattern = r'(version\s*=\s*["\'])([^"\']+)(["\'])'
    match = re.search(pattern, content)

    if not match:
        print(f"  ⊘ Could not find version in {setup_path}")
        return False

    old_version = match.group(2)
    new_content = re.sub(pattern, f'\\g<1>{new_version}\\g<3>', content)

    setup_path.write_text(new_content)
    print(f"  ✓ {package_dir.name}/setup.py: {old_version} -> {new_version}")
    return True


def update_init_py(package_dir, new_version):
    """Update version in __init__.py if it exists."""
    init_path = package_dir / '__init__.py'
    if not init_path.exists():
        return False

    content = init_path.read_text()

    # Match __version__ = "X.Y.Z" pattern
    pattern = r'(__version__\s*=\s*["\'])([^"\']+)(["\'])'
    match = re.search(pattern, content)

    if not match:
        return False

    old_version = match.group(2)
    new_content = re.sub(pattern, f'\\g<1>{new_version}\\g<3>', content)

    init_path.write_text(new_content)
    print(f"  ✓ {package_dir.name}/__init__.py: {old_version} -> {new_version}")
    return True


def get_current_version(package_dir):
    """Get current version from setup.py."""
    setup_path = package_dir / 'setup.py'
    if not setup_path.exists():
        return None

    content = setup_path.read_text()
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def bump_package_version(package_name, bump_type):
    """Bump version for a single package."""
    package_dir = Path(package_name)
    if not package_dir.exists():
        print(f"⊘ Package directory not found: {package_name}")
        return False

    print(f"\n{package_name}:")

    current_version = get_current_version(package_dir)
    if not current_version:
        print(f"  ⊘ Could not determine current version")
        return False

    new_version = bump_version(current_version, bump_type)

    success = update_setup_py(package_dir, new_version)
    update_init_py(package_dir, new_version)  # Optional, won't fail if missing

    return success


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    package = sys.argv[1]
    bump_type = sys.argv[2]

    if bump_type not in ['major', 'minor', 'patch']:
        print(f"Error: Invalid bump type '{bump_type}'")
        print("Must be: major, minor, or patch")
        sys.exit(1)

    print("=" * 50)
    print(f"Bumping version ({bump_type})")
    print("=" * 50)

    if package == 'all':
        # Bump all packages
        for pkg in PACKAGES:
            bump_package_version(pkg, bump_type)
    else:
        # Bump single package
        if package not in PACKAGES:
            print(f"Warning: '{package}' not in known packages list")
            print(f"Known packages: {', '.join(PACKAGES)}")
            print("Attempting anyway...")

        bump_package_version(package, bump_type)

    print("\n" + "=" * 50)
    print("Done! Don't forget to:")
    print("  1. Review the changes")
    print("  2. Commit the version bumps")
    print("  3. Tag the release (optional)")
    print("  4. Build and publish")
    print("=" * 50)


if __name__ == '__main__':
    main()
