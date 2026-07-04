#!/usr/bin/env python3
"""Verify and display encoding of SAGE files"""

import sys
from pathlib import Path

def check_file(file_path):
    """Check file encoding and display sample"""
    print(f"\n{'='*60}")
    print(f"File: {file_path.name}")
    print(f"{'='*60}")

    # Read as bytes
    data = file_path.read_bytes()

    # Try decoding
    try:
        text = data.decode('utf-8')
        print(f"✓ Valid UTF-8 encoding")

        # Count emojis
        emoji_count = sum(1 for c in text if ord(c) > 0x1F000)
        print(f"✓ Contains {emoji_count} emoji characters")

        # Show first few lines
        lines = text.split('\n')[:5]
        print(f"\nFirst 5 lines:")
        for i, line in enumerate(lines, 1):
            # Replace emojis with their code points for display
            safe_line = ''.join(c if ord(c) < 0x1F000 else f'[U+{ord(c):04X}]' for c in line)
            print(f"  {i}. {safe_line[:80]}")

        return True

    except UnicodeDecodeError as e:
        print(f"✗ Invalid UTF-8: {e}")
        return False

def main():
    """Main function"""
    files = [
        Path('README.md'),
        Path('SAGE_V2_COMPLETE.md'),
    ]

    print("SAGE Encoding Verification Tool")
    print("=" * 60)

    for file_path in files:
        if file_path.exists():
            check_file(file_path)
        else:
            print(f"\n✗ File not found: {file_path}")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("\nNote: Emojis shown as [U+XXXX] are correctly encoded.")
    print("If your terminal shows garbage, it's a display issue, not file corruption.")

if __name__ == '__main__':
    main()
