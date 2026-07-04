import os
import sys
from pathlib import Path

FIXES = {
    b'\xc3\xa2\xc2\x94\xc2\x9c\xc3\xa2\xc2\x94\xc2\x80\xc3\xa2\xc2\x94\xc2\x80': b'\xe2\x94\x9c\xe2\x94\x80\xe2\x94\x80',
    b'\xc3\xa2\xc2\x94\xc2\x82': b'\xe2\x94\x82',
    b'\xc3\xa2\xc2\x94\xc2\x94\xc3\xa2\xc2\x94\xc2\x80\xc3\xa2\xc2\x94\xc2\x80': b'\xe2\x94\x94\xe2\x94\x80\xe2\x94\x80',
    b'\xc3\xb0\xc2\x9f\xc2\xa7\xc2\xa0': b'\xf0\x9f\xa7\xa0',
    b'\xc3\xb0\xc2\x9f\xc2\x9a\xc2\x80': b'\xf0\x9f\x9a\x80',
    b'\xc3\xa2\xc2\x9c\xc2\x85': b'\xe2\x9c\x85',
}

root = Path.cwd()
count = 0

for f in root.rglob('*.md'):
    if '.git' in str(f): continue
    try:
        data = f.read_bytes()
        changed = False
        for bad, good in FIXES.items():
            if bad in data:
                data = data.replace(bad, good)
                changed = True
        if changed:
            f.write_bytes(data)
            print(f"Fixed: {f.name}")
            count += 1
    except: pass

print(f"Total fixed: {count}")
