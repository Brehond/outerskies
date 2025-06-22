#!/usr/bin/env python3
"""Fix whitespace issues in plugin template files."""

import os

def fix_file(filepath):
    """Fix whitespace issues in a file."""
    print(f"Fixing {filepath}...")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in lines]
    
    # Remove empty lines at the end
    while lines and lines[-1] == '':
        lines.pop()
    
    # Write back with single newline at end
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f"Fixed {filepath}")

def main():
    """Fix all plugin template files."""
    files = [
        'plugins/plugin_template/__init__.py',
        'plugins/plugin_template/plugin.py'
    ]
    
    for filepath in files:
        if os.path.exists(filepath):
            fix_file(filepath)
        else:
            print(f"File not found: {filepath}")
    
    print("All plugin template files fixed!")

if __name__ == '__main__':
    main() 