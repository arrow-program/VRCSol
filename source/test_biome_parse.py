#!/usr/bin/env python3
import os
import re

def normalize_biome_key(name: str):
    try:
        return re.sub(r'[^A-Za-z0-9]', '', (name or '').strip()).upper()
    except Exception:
        return (name or '').strip().upper()

# Read and parse biome message file
path = 'biome message.txt'
if not os.path.exists(path):
    print(f"File not found: {path}")
    exit(1)

messages = {}
print(f"Reading from {path}...\n")
with open(path, 'r', encoding='utf-8') as f:
    for i, raw in enumerate(f, 1):
        line = raw.strip()
        if not line:
            continue
        print(f"Line {i}: {repr(line)}")
        # Match optional (start)/(end), then [Biome]: message
        m = re.match(r'^(?:\((start|end)\)\s*)?\s*\[(.*?)\]\s*:\s*(.*)$', line, re.IGNORECASE)
        if not m:
            print(f"  -> NO MATCH\n")
            continue
        marker = m.group(1)
        biome = m.group(2)
        msg = m.group(3).strip()
        key = normalize_biome_key(biome)
        print(f"  -> MATCH: marker={marker}, biome={biome}, key={key}, msg={repr(msg[:30])}")
        d = messages.setdefault(key, {})
        if marker:
            if marker.lower() == 'start':
                d['start'] = msg
            elif marker.lower() == 'end':
                d['end'] = msg
        else:
            d['default'] = msg
        print()

print(f"\nTotal messages: {len(messages)}")
print(f"Keys: {list(messages.keys())}")
print(f"\nFull dict:")
for k, v in messages.items():
    print(f"  {k}: {v}")

# Test lookup for RAINY
print("\n--- Testing lookup ---")
lookup = 'RAINY'
key = normalize_biome_key(lookup)
print(f"Normalized '{lookup}' -> '{key}'")
print(f"Found in dict: {messages.get(key, 'NOT FOUND')}")
