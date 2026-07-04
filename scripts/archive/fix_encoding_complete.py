#!/usr/bin/env python3
"""Complete encoding fix script for all SAGE files"""

import os
import sys
from pathlib import Path
import re

# Comprehensive mojibake mappings
MOJIBAKE_FIXES = {
    # Tree characters
    'â"œâ"€â"€': '├──',
    'â"‚   â"œâ"€â"€': '│   ├──',
    'â"‚   â"‚   â"œâ"€â"€': '│   │   ├──',
    'â""â"€â"€': '└──',
    'â"‚   â""â"€â"€': '│   └──',
    'â"‚': '│',

    # Emoji
    'ðŸ§ ': '🧠',
    'ðŸš€': '🚀',
    'âœ…': '✅',
    'ðŸ"š': '📚',
    'ðŸ"Š': '📊',
    'ðŸ"¦': '📦',
    'ðŸ—‚ï¸�': '🗂️',
    'ðŸ"‹': '📋',
    'ðŸ¤–': '🤖',
    'ðŸ"': '🔍',
    'ðŸ"§': '🔧',
    'ðŸ'¡': '💡',
    'âš¡': '⚡',
    'ðŸŽ¯': '🎯',
    'ðŸ›¡ï¸�': '🛡️',
    'ðŸ"�': '🔐',
    'ðŸŒ': '🌐',
    'ðŸ"ˆ': '📈',
    'ðŸ"¥': '🔥',
    'ðŸŽ¨': '🎨',
    'ðŸ"': '📝',
    'âš™ï¸�': '⚙️',
    'ðŸ�—ï¸�': '🗂️',
    'ðŸ"�': '🔑',
    'ðŸ'»': '💻',
    'ðŸ›ï¸�': '🛠️',
    'âš ï¸�': '⚠️',
    'ðŸŽ"': '🎓',
    'ðŸš§': '🚧',
    'ðŸ¤': '🤝',
    'ðŸ›£ï¸�': '🛣️',
    'ðŸ"–': '📖',
    'ðŸ"œ': '📜',
    'ðŸ'¨â€�ðŸ'»': '👨‍💻',
    'ðŸ"ž': '📞',
    'ðŸŒŸ': '🌟',
    '✨': '✨',
    'ðŸ"¬': '🔬',
    'ðŸ"Œ': '🔌',
    'ðŸŽ²': '🎲',
    'ðŸ'¬': '💬',

    # Arrows and symbols
    'â†'': '→',
    'â†�': '→',
    'â€¢': '•',
    'â€"': '—',
    'â€�': '"',
    'â€�': '"',
    'â€™': ''',
    'â€˜': ''',
    'Â©': '©',
    'Â®': '®',
    'â„¢': '™',
    'â‰ˆ': '≈',
    'â‰ ': '≠',
    'â‰¤': '≤',
    'â‰¥': '≥',

    # Common UTF-8 sequences
    'ï¿½': '',  # Replacement character
    'Â ': ' ',  # Non-breaking space fix
    'Â': '',    # Stray Â

    # Additional patterns
    'ðŸ�': '🗂',
    'ï¸�': '️',
    'â€�': '–',
}

def fix_mojibake(text):
    """Fix all mojibake patterns in text"""
    for broken, fixed in MOJIBAKE_FIXES.items():
        text = text.replace(broken, fixed)

    # Remove any remaining mojibake patterns
    text = re.sub(r'[ðŸâ€][^\s]{0,10}ï¸�', '', text)
    text = re.sub(r'Â+', ' ', text)

    return text

def process_file(file_path):
    """Process a single file"""
    try:
        # Try reading with different encodings
        content = None
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                break
            except:
                continue

        if content is None:
            print(f"❌ Could not read: {file_path}")
            return False

        # Check if file needs fixing
        has_mojibake = any(broken in content for broken in MOJIBAKE_FIXES.keys())

        if not has_mojibake:
            return True

        # Fix mojibake
        fixed_content = fix_mojibake(content)

        # Write back as UTF-8
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(fixed_content)

        print(f"✅ Fixed: {file_path}")
        return True

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function"""
    root_dir = Path(__file__).parent

    # File patterns to process
    patterns = ['*.md', '*.py', '*.txt', '*.json', '*.yaml', '*.yml']

    # Exclude patterns
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}

    print("🔧 SAGE Encoding Fix Tool")
    print("=" * 60)
    print()

    files_processed = 0
    files_fixed = 0
    files_failed = 0

    # Walk through all files
    for root, dirs, files in os.walk(root_dir):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = Path(root) / file

            # Check if file matches patterns
            if not any(file_path.match(pattern) for pattern in patterns):
                continue

            files_processed += 1

            if process_file(file_path):
                files_fixed += 1
            else:
                files_failed += 1

    print()
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   Files processed: {files_processed}")
    print(f"   Files fixed: {files_fixed}")
    print(f"   Files failed: {files_failed}")
    print()

    if files_failed == 0:
        print("✅ All files processed successfully!")
    else:
        print(f"⚠️  {files_failed} files had errors")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
