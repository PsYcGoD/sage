#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix mojibake in SAGE_V2_COMPLETE.md"""

# Read file
with open('SAGE_V2_COMPLETE.md', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Fix all mojibake patterns - each separately
content = content.replace('�', '?')  # Replace replacement chars first

# Fix emojis
replacements = [
    ('📋', '📋'),  # Already correct in README
    ('✅', '✅'),
    ('📊', '📊'),
    ('🗂️', '🗂️'),
    ('🗄️', '🗄️'),
    ('🧪', '🧪'),
    ('💻', '💻'),
    ('⚙️', '⚙️'),
    ('🛠️', '🛠️'),
    ('📈', '📈'),
    ('🔒', '🔒'),
    ('🚢', '🚢'),
    ('🤝', '🤝'),
    ('📜', '📜'),
    ('🙏', '🙏'),
    ('📞', '📞'),
    ('🗺️', '🗺️'),
    ('📅', '📅'),
    ('🔄', '🔄'),
    ('🔮', '🔮'),
    ('█', '█'),
    ('░', '░'),
    ('🎉', '🎉'),
    ('🔗', '🔗'),
    ('💡', '💡'),
    ('⚠️', '⚠️'),
    ('→', '→'),
    ('├──', '├──'),
    ('│', '│'),
    ('└──', '└──'),
]

# Look for any ? sequences that look like corrupted chars
import re

# Find all sequences of question marks and nearby text
lines = content.split('\n')
fixed_lines = []

for line in lines:
    # Fix tree chars
    line = line.replace('???????', '├──')
    line = line.replace('????', '│')
    line = line.replace('???', '│')

    # Try to detect emoji positions by context
    if '## ???' in line:
        if 'PROJECT METADATA' in line:
            line = '## 📋 PROJECT METADATA'
        elif 'COMPLETE PROJECT STATISTICS' in line:
            line = '## 📊 COMPLETE PROJECT STATISTICS'
        elif 'COMPLETE FILE STRUCTURE' in line:
            line = '## 🗂️ COMPLETE FILE STRUCTURE'
        elif 'DATABASE SCHEMA' in line:
            line = '## 🗄️ DATABASE SCHEMA'
        elif 'TESTING' in line:
            line = '## 🧪 TESTING'
        elif 'DEVELOPMENT SETUP' in line:
            line = '## 💻 DEVELOPMENT SETUP'
        elif 'CONFIGURATION' in line:
            line = '## ⚙️ CONFIGURATION'
        elif 'KNOWN LIMITATIONS' in line:
            line = '## 🛠️ KNOWN LIMITATIONS'
        elif 'PERFORMANCE' in line:
            line = '## 📈 PERFORMANCE'
        elif 'SECURITY' in line:
            line = '## 🔒 SECURITY & PRIVACY'
        elif 'DEPLOYMENT' in line:
            line = '## 🚢 DEPLOYMENT'
        elif 'CONTRIBUTING' in line:
            line = '## 🤝 CONTRIBUTING'
        elif 'LICENSE' in line:
            line = '## 📜 LICENSE'
        elif 'ACKNOWLEDGMENTS' in line:
            line = '## 🙏 ACKNOWLEDGMENTS'
        elif 'SUPPORT' in line:
            line = '## 📞 SUPPORT'
        elif 'ROADMAP' in line:
            line = '## 🗺️ ROADMAP'
        elif 'PROJECT TIMELINE' in line:
            line = '## 📊 PROJECT TIMELINE'
        elif 'PROJECT STATUS' in line:
            line = '## 🎉 PROJECT STATUS'
        elif 'QUICK LINKS' in line:
            line = '## 🔗 QUICK LINKS'
        elif 'PHILOSOPHY' in line:
            line = '## 💡 PHILOSOPHY'

    # Fix other patterns
    if '### ??? Completed' in line:
        line = '### ✅ Completed (v2.0)'
    if '### ???' in line and 'In Progress' in line:
        line = '### 🔄 In Progress'
    if '### ???' in line and 'Planned' in line:
        line = '### 📅 Planned (v2.1)'
    if '### ???' in line and 'Future' in line:
        line = '### 🔮 Future (v3.0+)'

    # Fix timeline bars
    if '???' in line and ('2025' in line or '2026' in line):
        line = line.replace('???', '█')
        line = line.replace('??', '░')

    # Fix warning symbol
    if '? ??' in line and ('Prediction' in line or 'chance' in line):
        line = line.replace('? ??', '⚠️')

    # Fix arrows
    line = line.replace(' ??? ', ' → ')

    fixed_lines.append(line)

content = '\n'.join(fixed_lines)

# Write back
with open('SAGE_V2_COMPLETE.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed all mojibake in SAGE_V2_COMPLETE.md")
