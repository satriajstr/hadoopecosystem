"""Sorted district key, eligible/D1/D3 counts -> coverage and dropout."""
import sys
from decimal import Decimal, ROUND_HALF_UP


def percentage(numerator,denominator):
    return str((Decimal(100)*numerator/denominator).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)) if denominator else '\\N'


def emit(key,eligible,d1,d3):
    print(f'{key}\t{eligible}\t{d1}\t{d3}\t{percentage(d3,eligible)}\t{percentage(d1-d3,d1)}')


def main():
    current = None
    eligible = d1 = d3 = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        key,n,a,b = line.rstrip('\r\n').split('\t')
        n,a,b = map(int,(n,a,b))
        if n<=0 or not 0<=b<=a<=n:
            raise ValueError('Invalid partial district counts')
        if current is not None and key<current:
            raise ValueError('Reducer input must be sorted by key')
        if current is not None and key!=current:
            emit(current,eligible,d1,d3)
            eligible = d1 = d3 = 0
        current = key
        eligible += n
        d1 += a
        d3 += b
    if current is not None:
        emit(current,eligible,d1,d3)


if __name__=='__main__':
    main()
