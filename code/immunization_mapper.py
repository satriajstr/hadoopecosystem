"""Streaming mapper: five-country annual DTP3 estimates, emit sum/count."""
import sys
from decimal import Decimal

COUNTRIES = {'IDN': 'Indonesia', 'MYS': 'Malaysia', 'THA': 'Thailand',
             'VNM': 'Viet Nam', 'PHL': 'Philippines'}
YEARS = tuple(range(2020, 2026))


def map_record(line):
    fields = line.rstrip('\r\n').split('\t')
    if len(fields) != 10:
        raise ValueError('Expected ten columns in the WUENIC TSV')
    area, _, indicator, sex, year, coverage, unit, status, revision, age = fields
    if (area not in COUNTRIES or indicator != 'IM_DTP3' or sex != '_T'
            or unit != 'PCNT' or status != 'E' or int(year) not in YEARS):
        return None
    if coverage in ('', '\\N'):
        return None
    value = Decimal(coverage)
    if not value.is_finite() or not 0 <= value <= 100:
        raise ValueError('Coverage must be a finite percentage between 0 and 100')
    # Include metadata in the key, so different source revisions/ages never mix.
    key = '|'.join((area, indicator, sex, unit, status, revision, age))
    return f'{key}\t{value}\t1\n'


def main():
    for line in sys.stdin:
        if line.strip():
            mapped = map_record(line)
            if mapped is not None:
                sys.stdout.write(mapped)


if __name__ == '__main__':
    main()
