#!/usr/bin/env python3
import os

path = r'C:\Users\douzh\Desktop\vrcsol\biome message.txt'
print(f"File exists: {os.path.exists(path)}")
print(f"File size (bytes): {os.path.getsize(path) if os.path.exists(path) else 'N/A'}")

if os.path.exists(path):
    # Read raw bytes
    with open(path, 'rb') as f:
        raw_bytes = f.read()
    print(f"Raw bytes length: {len(raw_bytes)}")
    print(f"First 200 bytes (repr): {repr(raw_bytes[:200])}")
    print()
    
    # Read as text with different encodings
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1']:
        try:
            with open(path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            print(f"Encoding {encoding}: {len(lines)} lines")
            for i, line in enumerate(lines[:5], 1):
                print(f"  Line {i}: {repr(line)}")
            break
        except Exception as e:
            print(f"Encoding {encoding}: ERROR - {e}")
