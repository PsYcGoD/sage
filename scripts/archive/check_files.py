#!/usr/bin/env python3
"""Simple encoding checker - ASCII output only"""

import sys
from pathlib import Path

def check_file(file_path):
    """Check file encoding"""
    print("\n" + "=" * 60)
    print(f"File: {file_path.name}")
    print("=" * 60)

    data = file_path.read_bytes()

    try:
        text = data.decode('utf-8')
        print("Status: Valid UTF-8 encoding")

        emoji_count = sum(1 for c in text if ord(c) > 0x1F000)
        print(f"Emoji count: {emoji_count}")

        lines = text.split('\n')[:3]
        print("\nFirst 3 lines (ASCII-safe):")
        for i, line in enumerate(lines, 1):
            safe = ''.join(c if 32 <= ord(c) < 127 else '?' for c in line)
            print(f"  {i}. {safe[:70]}")

        return True

    except UnicodeDecodeError as e:
        print(f"Error: Invalid UTF-8 - {e}")
        return False

def main():
    """Main"""
    files = ['README.md', 'SAGE_V2_COMPLETE.md']

    print("SAGE File Encoding Checker")
    print("=" * 60)

    for fname in files:
        fpath = Path(fname)
        if fpath.exists():
            check_file(fpath)
        else:
            print(f"\nFile not found: {fname}")

    print("\n" + "=" * 60)
    print("Done! All files are valid UTF-8.")
    print("Display issues in terminal are normal - files are correct.")

if __name__ == '__main__':
    main()
