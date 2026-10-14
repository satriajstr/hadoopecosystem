"""Four repeatable WHO companion stages in Windows; no Hadoop services started."""
import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from immunization_mapper import COUNTRIES, YEARS
from run_immunization_mapreduce import main as run_mapreduce

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/manual-who'
FIELDS = ['area_code','area_name','indicator','sex','year','coverage_pct',
          'unit','observation_status','source_revision','age_group']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load_tsv(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream, fieldnames=FIELDS, delimiter='\t'))
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError('Incorrect TSV column count')
    return rows


def write_csv(path, fields, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def sql_results(path):
    rows = load_tsv(path)
    sql = (ROOT/'native/demo/hive_walkthrough.sql').read_text(encoding='utf-8')
    statements = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--')).split(';')
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE real_coverage_long (' + ','.join(
            f'{field} ' + ('INTEGER' if field=='year' else 'REAL' if field=='coverage_pct' else 'TEXT') for field in FIELDS) + ')')
        db.executemany('INSERT INTO real_coverage_long VALUES (?,?,?,?,?,?,?,?,?,?)',
            [tuple(None if row[field]=='\\N' else row[field] for field in FIELDS) for row in rows])
        results = []
        for statement in statements:
            if statement.strip():
                cursor = db.execute(statement)
                results.append({'sql':statement.strip(), 'columns':[col[0] for col in cursor.description], 'rows':cursor.fetchall()})
    return results


def filter_group(path):
    selected = [r for r in load_tsv(path) if r['area_code'] in COUNTRIES
        and int(r['year']) in YEARS and r['indicator'] in ('IM_DTP1','IM_DTP3')
        and r['sex']=='_T' and r['unit']=='PCNT' and r['observation_status']=='E'
        and r['coverage_pct'] not in ('','\\N') and 0<=float(r['coverage_pct'])<=100]
    selected.sort(key=lambda r:(r['area_code'], int(r['year']), r['indicator']))
    counts = sorted(Counter((r['area_code'],int(r['year'])) for r in selected).items())
    return selected, [(country,year,count) for (country,year),count in counts]


def storage():
    runs = OUT/'runs'
    runs.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=runs))
    folder = run/'storage'
    folder.mkdir()
    source = ROOT/'data/real/immunization_coverage_long.tsv'
    target = folder/'coverage.tsv'
    shutil.copyfile(source,target)
    assert digest(source)==digest(target)
    rows = load_tsv(target)
    info = {'run_id':run.name, 'input_relative':'storage/coverage.tsv',
        'source_sha256':digest(source), 'source_rows':len(rows),
        'created_at':datetime.now(timezone.utc).isoformat(),
        'countries':COUNTRIES, 'years':list(YEARS), 'last_jobs':{},
        'runtime':'Python filesystem copy; conceptual storage/HDFS demonstration; no HDFS execution'}
    save_json(run/'session.json',info)
    save_json(OUT/'latest.json',{'run_id':run.name})
    print('1. HDFS - PENYIMPANAN DATA IMUNISASI')
    print('Run:',run.name)
    print('Dataset internasional:',len(rows),'observasi;',target.stat().st_size,'byte')
    print('SHA-256 sumber dan salinan cocok.')
    for row in rows[:3]:
        print(row['area_code'],row['year'],row['indicator'],row['coverage_pct'])
    print('File:',target)
    return run


def stage(name):
    if not (OUT/'latest.json').exists():
        raise ValueError('Jalankan tahap storage terlebih dahulu: python code/manual_who_demo.py storage')
    run_id = json.loads((OUT/'latest.json').read_text(encoding='utf-8'))['run_id']
    run = (OUT/'runs'/run_id).resolve()
    if not run.is_relative_to((OUT/'runs').resolve()) or run.name!=run_id:
        raise ValueError('Invalid session path')
    info = json.loads((run/'session.json').read_text(encoding='utf-8'))
    source = run/'storage/coverage.tsv'
    if digest(source)!=info['source_sha256']:
        raise ValueError('Storage snapshot changed; create a new storage session')
    job = Path(tempfile.mkdtemp(prefix=name+'-', dir=run))
    if name=='mapreduce':
        print('2. MAPREDUCE + YARN - MAP, SHUFFLE/SORT, REDUCE')
        result = run_mapreduce(output_dir=job, input_path=source)
    elif name=='hive':
        print('3. HIVE - ANALISIS CAKUPAN DENGAN SQL')
        queries = sql_results(source)
        result = {'runtime':'SQLite', 'queries':queries, 'native_hive':'NOT RUN'}
        print('Observasi internasional:',queries[0]['rows'][0][0])
        print('Mean DTP3 per negara 2020-2025:')
        for row in queries[2]['rows']:
            print(row[0],row[1], 'sum=',row[4], 'tahun=',row[5], 'mean=',row[6])
        print('DTP1/DTP3 dan proxy dropout 2025:')
        for row in queries[4]['rows']:
            if row[2]==2025:
                print(row[0],row[1], 'DTP1=',row[3], 'DTP3=',row[4], 'gap=',row[5], 'proxy=',row[6])
        for i, query in enumerate(queries,1):
            write_csv(job/f'query-{i}.csv',query['columns'],query['rows'])
        if info['last_jobs'].get('mapreduce'):
            mr = json.loads((run/info['last_jobs']['mapreduce']/'results.json').read_text(encoding='utf-8'))
            actual = {row[0]:(int(row[5]),round(float(row[6]),2)) for row in queries[2]['rows']}
            expected = {row['area_code']:(row['year_count'],float(row['mean_yearly_coverage_pct'])) for row in mr['results']}
            if actual != expected:
                raise ValueError('SQL differs from MapReduce result')
            print('Hasil mean dan count cocok dengan MapReduce sesi ini.')
            result['matches_mapreduce'] = True
        save_json(job/'results.json',result)
    elif name=='pig':
        print('4. PIG - FILTER DAN PENGELOMPOKAN DATA')
        selected, counts = filter_group(source)
        write_csv(job/'filtered_countries.csv',FIELDS,([row[key] for key in FIELDS] for row in selected))
        write_csv(job/'grouped_country_year.csv',['area_code','year','indicator_rows'],counts)
        result = {'runtime':'Python filter/group', 'selected_rows':len(selected),
                  'grouped_rows':counts, 'native_pig':'NOT RUN'}
        save_json(job/'results.json',result)
        print(info['source_rows'],'observasi ->',len(selected),'baris terpilih ->',len(counts),'kelompok negara/tahun')
        for country in sorted(COUNTRIES):
            country_groups = [row for row in counts if row[0]==country]
            print(country, len(country_groups),'tahun;',sum(row[2] for row in country_groups),'observasi indikator')
        print('Setiap kelompok memiliki dua observasi indikator, bukan dua anak.')
    else:
        raise ValueError('Unknown stage')
    info['last_jobs'][name] = job.name
    save_json(run/'session.json',info)
    print('Hasil percobaan:',job)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['storage','mapreduce','hive','pig','all'])
    args = parser.parse_args()
    if args.stage in ('storage','all'):
        storage()
    if args.stage=='all':
        for name in ('mapreduce','hive','pig'):
            stage(name)
    elif args.stage!='storage':
        stage(args.stage)


if __name__ == '__main__':
    main()
