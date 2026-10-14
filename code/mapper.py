#!/usr/bin/env python3
"""Hadoop Streaming: satu pasangan (kata, 1) untuk setiap token."""
import sys

for line in sys.stdin:
    # Sama dengan modul: token dipisahkan whitespace, case-sensitive.
    for word in line.strip().split():
        print(f"{word}\t1")
