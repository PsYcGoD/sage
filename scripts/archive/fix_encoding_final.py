#!/usr/bin/env python3
"""Complete encoding fix script for all SAGE files"""

import os
import sys
from pathlib import Path
import re

# Comprehensive mojibake mappings - using hex escape codes to avoid mojibake in script itself
MOJIBAKE_FIXES = {
    # Tree characters
    '├──': '├──',
    '│   ├──': '│   ├──',
    '│   │   ├──': '│   │   ├──',
    '└──': '└──',
    '│   └──': '│   └──',
    '│': '│',

    # Common broken patterns
    'â"œâ"€â"€': '├──',
    'â"‚': '│',
    'â""â"€â"€': '└──',
    'â†'': '→',
    'â€¢': '•',
    'â€"': '—',
    'â€�': '"',
    'â€™': ''',
    'âœ…': '✅',
    'ðŸ§ ': '🧠',
    'ðŸš€': '🚀',
    'ðŸ"š': '📚',
    'ðŸ"Š': '📊',
    'ðŸ"¦': '📦',
    'ðŸ—‚ï¸�': '🗂️',
    'ðŸ�—ï¸�': '🗂️',
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
    'ðŸ"¬': '🔬',
    'ðŸ"Œ': '🔌',
    'ðŸŽ²': '🎲',
    'ðŸ'¬': '💬',

    # Cleanup patterns
    'ï¿½': '',
    'Â ': ' ',
    'Â': '',
}

def fix_mojibake(text):
    """Fix all mojibake patterns in text"""
    original = text

    # Apply all fixes
    for broken, fixed in MOJIBAKE_FIXES.items():
        text = text.replace(broken, fixed)

    # Clean up remaining broken UTF-8
    text = re.sub(r'[ðŸâ€][^\s]{0,10}ï¸�', '', text)
    text = re.sub(r'Â+', ' ', text)
    text = re.sub(r'â€[^\s]{0,3}', '', text)
    text = re.sub(r'â\x9c[^\s]', '', text)

    return text

def process_file(file_path):
    """Process a single file"""
    try:
        # Read file with error handling
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                break
            except:
                continue

        if content is None:
            return False

        # Check if needs fixing
        needs_fix = any(broken in content for broken in MOJIBAKE_FIXES.keys())
        if not needs_fix:
            return True

        # Fix and write back
        fixed_content = fix_mojibake(content)

        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(fixed_content)

        print(f"Fixed: {file_path.relative_to(Path.cwd())}")
        return True

    except Exception as e:
        print(f"Error: {file_path}: {e}")
        return False

def main():
    """Main function"""
    root_dir = Path.cwd()

    patterns = ['*.md', '*.py', '*.txt', '*.json', '*.yaml', '*.yml']
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}

    print("SAGE Encoding Fix Tool")
    print("=" * 60)

    files_processed = 0
    files_fixed = 0

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = Path(root) / file

            if any(file_path.match(pattern) for pattern in patterns):
                files_processed += 1
                if process_file(file_path):
                    files_fixed += 1

    print("=" * 60)
    print(f"Processed: {files_processed} | Fixed: {files_fixed}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
