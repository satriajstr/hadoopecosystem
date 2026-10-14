"""Dummy child TSV -> district key and eligible/D1/D3 counts."""
import sys


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        fields = line.rstrip('\r\n').split('\t')
        if len(fields)!=10:
            raise ValueError('Registry TSV requires ten columns')
        _,province,district,_,year,due,d1,d2,d3,_ = fields
        year,due,d1,d2,d3 = map(int,(year,due,d1,d2,d3))
        if any(value not in (0,1) for value in (due,d1,d2,d3)) or not d3<=d2<=d1:
            raise ValueError('Invalid eligibility/dose sequence')
        if year==2023 and due==1:
            print(f'{province}|{district}\t1\t{d1}\t{d3}')


if __name__=='__main__':
    main()
