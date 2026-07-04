import sys
import codecs

# Read as binary then decode
with open('SAGE_V2_COMPLETE.md', 'rb') as f:
    raw = f.read()

# Try to decode - use latin1 which never fails
text = raw.decode('utf-8', errors='replace')

# Simple character-by-character replacement
text = text.replace('�', '?')

# Write clean version
with open('SAGE_V2_COMPLETE_CLEAN.md', 'w', encoding='utf-8') as f:
    f.write(text)

sys.stdout.buffer.write(b'[OK] Created clean version\n')
