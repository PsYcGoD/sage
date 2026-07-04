#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Mojibake Nuclear Fix - Handles all corruption patterns
"""
import re
import sys
from pathlib import Path

# Force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Comprehensive mojibake mapping
MOJIBAKE_MAP = {
    # Emojis
    r"M-pM-\^_M-'M-\s*": '🔷 ',
    r"M-pM-\^_M-\^ZM-\^@": '📋',
    r"M-bM-\^\\M-\(": '✨',
    r"M-pM-\^_M-\^NM-/": '🎯',
    r"M-pM-\^_M-\^TM-'": '🔧',
    r"M-bM-\^ZM-!": '⚡',
    r"M-bM-\^\\M-\^E": '✅',
    r"M-pM-\^_M-\^SM-\^K": '📊',
    r"M-oM-;M-\?": '',  # BOM - remove it

    # Punctuation
    r"M-bM-\^@M-\^T": '—',  # em dash
    r"M-bM-\^@M-\^S": '–',  # en dash
    r"M-bM-\^@M-\^Y": ''',  # left single quote
    r"M-bM-\^@M-\^Z": ''',  # right single quote
    r"M-bM-\^@M-\^\[": '"',  # left double quote
    r"M-bM-\^@M-\^\\": '"',  # right double quote
    r"M-bM-\^@M-\&": '…',   # ellipsis

    # Control chars
    r"\^M\$": '',  # CRLF
    r"\^M": '',    # CR

    # Cat -A artifacts
    r"\$\n": '\n',
}

def fix_file(filepath: Path) -> tuple[bool, str]:
    """Fix a single file, return (changed, message)"""
    try:
        # Try reading with different encodings
        content = None
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return False, f"❌ Could not decode {filepath.name}"

        original = content

        # Apply all mojibake fixes
        for pattern, replacement in MOJIBAKE_MAP.items():
            content = re.sub(pattern, replacement, content)

        # Additional cleanup
        content = re.sub(r'\r\n', '\n', content)  # Normalize line endings
        content = re.sub(r'\r', '\n', content)
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines
        content = content.strip() + '\n'

        if content != original:
            # Backup original
            backup = filepath.with_suffix(filepath.suffix + '.bak')
            with open(backup, 'w', encoding='utf-8') as f:
                f.write(original)

            # Write cleaned version
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            changes = len([m for p in MOJIBAKE_MAP.keys() if re.search(p, original)])
            return True, f"✅ Fixed {filepath.name} ({changes} patterns corrected)"

        return False, f"✓ {filepath.name} already clean"

    except Exception as e:
        return False, f"❌ Error fixing {filepath.name}: {e}"

def main():
    sage_root = Path(__file__).parent

    # Files to fix
    targets = [
        sage_root / 'README.md',
        sage_root / 'SAGE_V2_COMPLETE.md',
    ]

    # Also find any other .md files with issues
    for md_file in sage_root.rglob('*.md'):
        if md_file not in targets and not any(x in str(md_file) for x in ['.git', '__pycache__', 'node_modules', '_backup']):
            targets.append(md_file)

    print("SAGE Mojibake Nuclear Fix\n")
    print(f"Scanning {len(targets)} files...\n")

    fixed_count = 0
    for filepath in targets:
        if filepath.exists():
            changed, msg = fix_file(filepath)
            print(msg)
            if changed:
                fixed_count += 1

    print(f"\n{'='*50}")
    print(f"Fixed {fixed_count} files")
    print(f"Backups saved with .bak extension")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
