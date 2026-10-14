#!/usr/bin/env python3
"""Input harus sudah dikelompokkan/diurutkan berdasarkan key oleh shuffle."""
import sys

current_word = None
total = 0
for line in sys.stdin:
    if not line.strip():
        continue
    word, count = line.rstrip("\n").split("\t", 1)
    if current_word is not None and word != current_word:
        print(f"{current_word}\t{total}")
        total = 0
    current_word = word
    total += int(count)

if current_word is not None:
    print(f"{current_word}\t{total}")
