#!/usr/bin/env python3
"""
Version bump script for kion-mcp project.

Updates both manifest.json and pyproject.toml to the next minor semver version.
Usage: python scripts/version_bump.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple


def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into major, minor, patch components."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-.*)?$', version.strip())
    if not match:
        raise ValueError(f"Invalid semantic version format: {version}")
    
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def increment_minor_version(version: str) -> str:
    """Increment the minor version and reset patch to 0."""
    major, minor, patch = parse_semver(version)
    return f"{major}.{minor + 1}.0"


def update_manifest_json(file_path: Path, new_version: str) -> bool:
    """Update version in manifest.json file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        old_version = data.get('version', 'unknown')
        data['version'] = new_version
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        print(f"Updated {file_path}: {old_version} -> {new_version}")
        return True
    
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error updating {file_path}: {e}", file=sys.stderr)
        return False


def update_pyproject_toml(file_path: Path, new_version: str) -> bool:
    """Update version in pyproject.toml file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the version line in the [project] section
        version_pattern = r'(version\s*=\s*["\'])([^"\']+)(["\'])'
        match = re.search(version_pattern, content)
        
        if not match:
            print(f"Error: Could not find version field in {file_path}", file=sys.stderr)
            return False
        
        old_version = match.group(2)
        updated_content = re.sub(
            version_pattern,
            f'{match.group(1)}{new_version}{match.group(3)}',
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"Updated {file_path}: {old_version} -> {new_version}")
        return True
    
    except FileNotFoundError as e:
        print(f"Error updating {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main function to bump version in both files."""
    project_root = Path(__file__).parent.parent
    manifest_path = project_root / "manifest.json"
    pyproject_path = project_root / "pyproject.toml"
    
    # Check if both files exist
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)
    
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)
    
    # Read current version from manifest.json
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        current_version = manifest_data['version']
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading version from {manifest_path}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Calculate new version
    try:
        new_version = increment_minor_version(current_version)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Bumping version from {current_version} to {new_version}")
    
    # Update both files
    success = True
    success &= update_manifest_json(manifest_path, new_version)
    success &= update_pyproject_toml(pyproject_path, new_version)
    
    if success:
        print(f"✅ Successfully bumped version to {new_version}")
        print("\nNext steps:")
        print("  1. Review the changes")
        print("  2. Commit the updated files")
        print("  3. Create a git tag: git tag -a v{} -m 'Release v{}'".format(new_version, new_version))
        print("  4. Push the tag: git push origin v{}".format(new_version))
    else:
        print("❌ Version bump failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
