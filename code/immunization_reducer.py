"""Sorted streaming input: key TAB sum_of_year_percentages TAB year_count."""
import sys
from decimal import Decimal, ROUND_HALF_UP


def emit(key, total, count):
    mean = (total / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    print(f'{key}\t{total}\t{count}\t{mean}')


current_key = None
total = Decimal(0)
count = 0
for line in sys.stdin:
    if not line.strip():
        continue
    key, value_text, count_text = line.rstrip('\r\n').split('\t')
    value, n = Decimal(value_text), int(count_text)
    if not value.is_finite() or n <= 0:
        raise ValueError('Reducer needs a finite sum and a positive count')
    if current_key is not None and key != current_key:
        emit(current_key, total, count)
        total, count = Decimal(0), 0
    current_key = key
    total += value
    count += n
if current_key is not None:
    emit(current_key, total, count)
