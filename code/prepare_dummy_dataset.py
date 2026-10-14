"""Deterministic fictional registry; dates and eligibility are teaching assumptions."""
import csv
import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from indonesia_regions import REGIONS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'data/dummy'
FIELDS = ['child_id','province','district','birth_date','birth_year','dose3_due',
          'dose1','dose2','dose3','last_updated']
EVENT_FIELDS = ['child_id','vaccine','dose_number','vaccination_date','facility_id']
COHORT = 2023
DEFAULT_CHILD = 'D000030'
DEFAULT_CHILDREN = 80137
DEFAULT_PROVINCES = 12
# The first 50 profiles retain a small teaching example; larger groups use
# district-specific dose totals instead of repeating the same percentages.
SCENARIOS = [(45,25),(45,40),(0,0),(50,45),(40,30),(35,15)]


def nearest_distinct_count(target,lower,upper,used,percentage):
    """Choose actual child counts whose displayed percentage is not repeated."""
    target = max(lower,min(upper,target))
    for distance in range(upper-lower+1):
        for candidate in (target+distance,target-distance):
            if lower<=candidate<=upper and percentage(candidate) not in used:
                used.add(percentage(candidate))
                return candidate
    # Very small optional configurations can exhaust the available integer
    # counts. Preserve a valid registry rather than inventing a percentage.
    used.add(percentage(target))
    return target


def dose_totals(size,district_index,seed_limits,used_coverage,used_dropout):
    """Deterministic district quotas, with one zero-denominator teaching case."""
    if district_index==2:  # Kabupaten Semarang: retain D1=0 and dropout N/A.
        used_coverage.add(0.0)
        return (0,0,0)
    seed1,seed2,seed3 = seed_limits
    base1,base3 = SCENARIOS[district_index%len(SCENARIOS)]
    # Basis points make small variations reproducible without a random source.
    rate3 = base3*200+37+(district_index*43)%227
    rate1 = base1*200-23-(district_index*29)%173
    if base1==0:
        rate3 = 125+(district_index*31)%239
        rate1 = rate3+700+(district_index*17)%181
    target3 = (size*rate3+5000)//10000
    count3 = nearest_distinct_count(target3,seed3,size-max(1,seed1-seed3),used_coverage,
                                   lambda count:round(100.0*count/size,2))
    target1 = (size*rate1+5000)//10000
    count1 = nearest_distinct_count(target1,max(seed1,count3+1,seed1+count3-seed3),size,used_dropout,
                                   lambda count:round(100.0*(count-count3)/count,2))
    count2 = max(seed2+count3-seed3,min(seed2+count1-seed1,(count1+count3)//2))
    return (count1,count2,count3)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def write_csv(path, fields, rows, delimiter=',', header=True):
    with Path(path).open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields,delimiter=delimiter)
        if header:
            writer.writeheader()
        writer.writerows(rows)


def generate(total_children=1200,provinces=3):
    if not isinstance(total_children,int) or total_children<1200 or total_children>1000000:
        raise ValueError('Jumlah anak harus 1.200 sampai 1.000.000')
    if not isinstance(provinces,int) or not 1<=provinces<=len(REGIONS):
        raise ValueError('Jumlah provinsi harus 1 sampai 38')
    if total_children<provinces*400:
        raise ValueError(f'Untuk {provinces} provinsi dibutuhkan minimal {provinces*400} anak '
                         '(dua kabupaten, empat tahun lahir, minimal 50 anak per kelompok)')
    children, events = [], []
    groups = provinces*2*4
    base,remainder = divmod(total_children,groups)
    # Each province has eight district/year groups. Offsets sum to zero and
    # keep all groups at least 50 children, including the smallest fixture.
    variation = min(3,base-50)
    offsets = (-3,1,2,0,3,-1,-2,0)
    used_coverage,used_dropout = set(),set()
    for district_index in range(provinces*2):
        d1,d3 = SCENARIOS[district_index%len(SCENARIOS)]
        province, districts = REGIONS[district_index//2]
        district = districts[district_index%2]
        for year_index,year in enumerate((2023,2022,2024,2025)):
            group_index = district_index*4+year_index
            offset = max(-variation,min(variation,offsets[group_index%8]))
            size = base+int(group_index<remainder)+offset
            limits = (d1,(d1+d3)//2,d3)
            if size>=100:
                # Only the analysis cohort needs unique percentages across
                # districts; other birth years use the same quota design.
                totals = dose_totals(size,district_index,limits,
                    used_coverage if year==COHORT else set(),
                    used_dropout if year==COHORT else set())
            else:
                totals = None  # Preserve the tiny 50-child teaching fixture.
            for rank in range(size):
                due = int(year!=2025)
                if totals is None or rank<50:
                    doses = [int(due and rank%50<limit) for limit in limits]
                else:
                    doses = [int(due and rank-50<count-seed)
                             for count,seed in zip(totals,limits)]
                child_id = f'D{len(children)+1:06d}'
                children.append(dict(zip(FIELDS,[child_id,province,district,
                    f'{year}-01-{rank%28+1:02d}',year,due,*doses,'2026-10-01'])))
                for dose,received in enumerate(doses,1):
                    if received:
                        events.append(dict(zip(EVENT_FIELDS,[child_id,'DTP',dose,
                            f'{year}-{5+dose:02d}-01',f'FAC{district_index+1:02d}'])))
    validate(children,events)
    return children,events


def validate(children,events):
    profiles = {}
    for row in children:
        if set(row)!=set(FIELDS) or any(value is None or str(value)=='' for value in row.values()):
            raise ValueError('Child fields missing or unexpected')
        child_id = row['child_id']
        if child_id in profiles:
            raise ValueError('Duplicate child ID')
        for key in ('birth_year','dose3_due','dose1','dose2','dose3'):
            row[key] = int(row[key])
        if any(row[key] not in (0,1) for key in ('dose3_due','dose1','dose2','dose3')):
            raise ValueError('Dose/eligibility flags must be 0 or 1')
        if not row['dose3']<=row['dose2']<=row['dose1']:
            raise ValueError('Dose sequence is inconsistent')
        birth = date.fromisoformat(row['birth_date'])
        if birth.year!=row['birth_year'] or date.fromisoformat(row['last_updated'])<birth:
            raise ValueError('Birth year/date or snapshot date inconsistent')
        profiles[child_id] = row
    seen, counts, dates = set(), Counter(), {}
    for event in events:
        if set(event)!=set(EVENT_FIELDS) or any(value is None or str(value)=='' for value in event.values()):
            raise ValueError('Event fields missing or unexpected')
        event['dose_number'] = int(event['dose_number'])
        child_id,dose = event['child_id'],event['dose_number']
        key = (child_id,dose)
        if child_id not in profiles or dose not in (1,2,3) or event['vaccine']!='DTP' or key in seen:
            raise ValueError('Unknown child, vaccine/dose, or duplicate event')
        vaccination = date.fromisoformat(event['vaccination_date'])
        profile = profiles[child_id]
        if not date.fromisoformat(profile['birth_date'])<=vaccination<=date.fromisoformat(profile['last_updated']):
            raise ValueError('Vaccination date outside profile lifetime/snapshot')
        seen.add(key)
        counts[key] += 1
        dates[key] = vaccination
    for child_id,row in profiles.items():
        for dose in (1,2,3):
            if counts[child_id,dose]!=row[f'dose{dose}']:
                raise ValueError('Profile status and vaccination history differ')
            if dose>1 and (child_id,dose) in dates and dates[child_id,dose]<=dates[child_id,dose-1]:
                raise ValueError('Vaccination dates out of dose order')


def load(folder=DATA):
    def read_csv(name,fields):
        with (Path(folder)/name).open(encoding='utf-8',newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames!=fields:
                raise ValueError('Unexpected registry schema')
            return list(reader)
    children = read_csv('children.csv',FIELDS)
    events = read_csv('vaccination_events.csv',EVENT_FIELDS)
    validate(children,events)
    # TSV used by mapper/native code must match the validated CSV exactly.
    with (Path(folder)/'children.tsv').open(encoding='utf-8',newline='') as stream:
        tsv = list(csv.reader(stream,delimiter='\t'))
    if tsv!=[[str(row[key]) for key in FIELDS] for row in children]:
        raise ValueError('TSV differs from validated CSV')
    return children,events


def main():
    parser = argparse.ArgumentParser(description='Buat registri buatan dengan ukuran dan jumlah provinsi yang dipilih.')
    parser.add_argument('--children',type=int,default=DEFAULT_CHILDREN,help='Jumlah anak, default 80.137')
    parser.add_argument('--provinces',type=int,default=DEFAULT_PROVINCES,help='Jumlah provinsi Indonesia, default 12; dua kabupaten/kota contoh per provinsi')
    args = parser.parse_args()
    try:
        children,events = generate(args.children,args.provinces)
    except ValueError as error:
        parser.error(str(error))
    DATA.mkdir(parents=True,exist_ok=True)
    write_csv(DATA/'children.csv',FIELDS,children)
    write_csv(DATA/'children.tsv',FIELDS,children,delimiter='\t',header=False)
    write_csv(DATA/'vaccination_events.csv',EVENT_FIELDS,events)
    save_json(DATA/'metadata.json',{
        'synthetic':True,'generator':'code/prepare_dummy_dataset.py; deterministic scenario v5; district-specific dose quotas',
        'coverage_design':'Distinct rounded D3 coverage and numeric dropout per district in the default presentation dataset; deliberately synthetic, not an empirical property',
        'geography':{'real_region_names':True,'reference':'source/regions/README.md',
                     'warning':'Synthetic immunization data; not actual coverage in these regions'},
        'parameters':{'children':args.children,'provinces':args.provinces},
        'allocation':'Even allocation across district/birth-year groups; remainder distributed to first groups; deterministic offsets of at most 3 children per group with zero net change',
        'children':len(children),'vaccination_events':len(events),
        'provinces':args.provinces,'districts':args.provinces*2,'birth_years':[2022,2023,2024,2025],
        'analysis_cohort':COHORT,'default_lookup_child':DEFAULT_CHILD,
        'snapshot_date':'2026-10-01','eligibility_rule':'Invented dose3_due flag for teaching; not a clinical schedule',
        'dates':'Invented chronological dates; not a recommended vaccination schedule',
        'quality':'IDs unique; flags and events consistent; dates ordered; unknown status absent by design',
        'sha256':{name:digest(DATA/name) for name in ('children.csv','children.tsv','vaccination_events.csv')}})
    cohort = [r for r in children if r['birth_year']==COHORT and r['dose3_due']]
    d3 = sum(r['dose3'] for r in cohort)
    print('DATA DUMMY:',len(children),'anak;',args.provinces,'provinsi Indonesia;',args.provinces*2,'kabupaten/kota contoh;',len(events),'catatan dosis.')
    print('Kelahiran 2023:',len(cohort),'memenuhi syarat;',d3,'sudah D3;',len(cohort)-d3,'belum D3.')
    print('Nama wilayah asli Indonesia; data anak dan imunisasi sintetis, bukan kondisi daerah sebenarnya.')
    print('Synthetic eligibility/dates are not clinical rules. Saved:',DATA)


if __name__=='__main__':
    main()
