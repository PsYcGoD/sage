#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive mojibake fix for SAGE_V2_COMPLETE.md"""

# Read file as bytes, try UTF-8 first
try:
    with open('SAGE_V2_COMPLETE.md', 'rb') as f:
        raw = f.read()

    # Try to decode as windows-1252 (common mojibake source) then re-encode properly
    try:
        content = raw.decode('windows-1252')
    except:
        content = raw.decode('utf-8', errors='replace')

    # Now fix all the known corruptions
    fixes = {
        # Emojis
        'ðŸ"‹': '📋',
        'âœ…': '✅',
        'ðŸ"Š': '📊',
        'ðŸ—‚ï¸': '🗂️',
        'ðŸ—„ï¸': '🗄️',
        'ðŸ§ª': '🧪',
        'ðŸ'»': '💻',
        'âš™ï¸': '⚙️',
        'ðŸ›': '🛠️',
        'ðŸ"ˆ': '📈',
        'ðŸ"'': '🔒',
        'ðŸš¢': '🚢',
        'ðŸ¤': '🤝',
        'ðŸ"œ': '📜',
        'ðŸ™': '🙏',
        'ðŸ"ž': '📞',
        'ðŸ—ºï¸': '🗺️',
        'ðŸ"…': '📅',
        'ðŸ"„': '🔄',
        'ðŸ"®': '🔮',
        'ðŸŽ‰': '🎉',
        'ðŸ"—': '🔗',
        'ðŸ'¡': '💡',
        'âš ï¸': '⚠️',

        # Box drawing characters
        'â"œâ"€â"€': '├──',
        'â"‚': '│',
        'â""â"€â"€': '└──',

        # Arrows and other symbols
        'â†'': '→',
        'â–ˆ': '█',
        'â–'': '░',
    }

    for bad, good in fixes.items():
        content = content.replace(bad, good)

    # Write back as proper UTF-8
    with open('SAGE_V2_COMPLETE.md', 'w', encoding='utf-8', newline='') as f:
        f.write(content)

    print("[OK] Fixed mojibake successfully!")

except Exception as e:
    print(f"[ERROR] Failed: {e}")
