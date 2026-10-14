"""Repeatable Hadoop Ecosystem concept demo using a fictional child registry."""
import argparse
import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from prepare_dummy_dataset import (ROOT, DATA, FIELDS, COHORT, DEFAULT_CHILD,
                                  digest, save_json, write_csv, load)
from concept_storage import demonstrate_storage, verify_storage, print_storage
from concept_yarn import YarnApplication, print_yarn

OUT = ROOT/'output/manual-demo'
STAGES = ('mapreduce','hive','pig','hbase')
ANALYSES = ('coverage','highest','lowest','overall','province','all')
ANALYSIS_FIELDS = ['eligible_children','dose1_children','dose3_children','dropout_children',
                   'missed_dose3','never_started_dose1','coverage_pct','dropout_pct']


def load_sql_table(db,children):
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE vaccinations ('+','.join(
        f'{key} '+('INTEGER' if key in ('birth_year','dose3_due','dose1','dose2','dose3') else 'TEXT')
        for key in FIELDS)+')')
    db.executemany('INSERT INTO vaccinations VALUES (?,?,?,?,?,?,?,?,?,?)',
                  [tuple(row[key] for key in FIELDS) for row in children])


def sql_coverage(children):
    query = (ROOT/'native/registry/coverage.sql').read_text(encoding='utf-8')
    with sqlite3.connect(':memory:') as db:
        load_sql_table(db,children)
        return [dict(row) for row in db.execute(query)]


def sql_analysis(children,limit=5):
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('Jumlah hasil harus 1 sampai 100')
    reports = {}
    with sqlite3.connect(':memory:') as db:
        load_sql_table(db,children)
        for name in ('overall','highest','lowest','province'):
            query = (ROOT/f'native/registry/analysis_{name}.sql').read_text(encoding='utf-8')
            query = query.replace('LIMIT 5;',f'LIMIT {limit};')
            rows = [dict(row) for row in db.execute(query)]
            reports[name] = rows[0] if name=='overall' else rows
    return reports


def filter_cohort(children):
    cohort = [row for row in children if row['birth_year']==COHORT and row['dose3_due']==1]
    return cohort,[row for row in cohort if row['dose3']==0]


def filter_followup(children,province=None,district=None):
    if district and not province:
        raise ValueError('Untuk memilih kabupaten, isi --province juga')
    if province and not any(row['province']==province for row in children):
        raise ValueError('Provinsi tidak ditemukan dalam dataset')
    if district and not any(row['province']==province and row['district']==district for row in children):
        raise ValueError('Kabupaten tidak ditemukan pada provinsi yang dipilih')
    cohort,_ = filter_cohort(children)
    cohort = [row for row in cohort if (not province or row['province']==province)
              and (not district or row['district']==district)]
    missed = [row for row in cohort if row['dose3']==0]
    dropout = [row for row in missed if row['dose1']==1]
    not_started = [row for row in missed if row['dose1']==0]
    return cohort,missed,dropout,not_started


def print_analysis(reports,analysis,limit,detail=False):
    percentage = lambda value:'N/A' if value is None else f'{value:.2f}%'.replace('.',',')
    if analysis in ('overall','all'):
        total = reports['overall']
        print('KESELURUHAN WILAYAH DALAM DATASET (kohort 2023)')
        print('Anak dihitung:',total['eligible_children'],'| sudah D1:',total['dose1_children'],
              '| sudah D3:',total['dose3_children'])
        print('Cakupan D3:',percentage(total['coverage_pct']))
        print('Putus lanjut D1 -> D3:',total['dropout_children'],'/',total['dose1_children'],
              '=',percentage(total['dropout_pct']))
        print('Belum D3:',total['missed_dose3'],'= putus lanjut',total['dropout_children'],
              '+ belum memulai D1',total['never_started_dose1'])
        if detail:
            print('Persentase memakai total jumlah anak; bukan rata-rata persentase kabupaten.')
    for name,label in (('highest','TERTINGGI'),('lowest','TERENDAH')):
        if analysis in (name,'all'):
            print(f'TOP {limit} KABUPATEN: PUTUS LANJUT {label}')
            print('No | Provinsi / Kabupaten | D1 | D3 | Putus lanjut (anak) | Putus lanjut %')
            for rank,row in enumerate(reports[name],1):
                print(rank,'|',row['province'],row['district'],'|',row['dose1_children'],
                      '|',row['dose3_children'],'|',row['dropout_children'],'|',percentage(row['dropout_pct']))
            if detail:
                print('D1 = 0 tidak masuk ranking. Nilai sama diurutkan menurut nama provinsi/kabupaten.')
    if analysis in ('province','all'):
        print('PERBANDINGAN PROVINSI DALAM DATASET')
        print('Provinsi | Anak dihitung | D1 | D3 | Cakupan D3 | Putus lanjut')
        for row in reports['province']:
            print(row['province'],'|',row['eligible_children'],'|',row['dose1_children'],
                  '|',row['dose3_children'],'|',percentage(row['coverage_pct']),
                  '|',percentage(row['dropout_pct']))
    if detail:
        print('Cakupan wilayah terbatas pada dataset sintetis; bukan statistik seluruh Indonesia.')


def history_index(children,events):
    index = {row['child_id']:{'profile':row,'history':[]} for row in children}
    for event in events:
        index[event['child_id']]['history'].append(event)
    for record in index.values():
        record['history'].sort(key=lambda row:row['dose_number'])
    return index


def lookup(children,events,child_id,index=None):
    found = (history_index(children,events) if index is None else index).get(child_id)
    if found is None:
        return {'child_id':child_id,'found':False,'profile':None,'history':[], 'missing_due_doses':[]}
    profile = found['profile']
    return {'child_id':child_id,'found':True,**found,
        'missing_due_doses':[f'DTP{dose}' for dose in (1,2,3) if not profile[f'dose{dose}']]
            if profile['dose3_due'] else []}


def column_cells(found):
    if not found['found']:
        return []
    cells = [{'row_key':found['child_id'],'family':'profile','qualifier':key,'value':str(value)}
             for key,value in found['profile'].items() if key!='child_id']
    cells.extend({'row_key':found['child_id'],'family':'history',
                  'qualifier':f'DTP{event["dose_number"]}',
                  'value':event['vaccination_date']+'|'+event['facility_id']}
                 for event in found['history'])
    return cells


def hbase_script(found):
    # Only a sample row import. Not a bulk synchronization/integration pipeline.
    lines = ['# Example profile/history columns for a synthetic child row.',
             '# Run create once; for an existing table use put/get only.',
             "create 'modul4_registry_demo', 'profile', 'history'"]
    if found['found']:
        quote = lambda value:json.dumps(str(value),ensure_ascii=False)
        for cell in column_cells(found):
            column = cell['family']+':'+cell['qualifier']
            lines.append(f'put "modul4_registry_demo", {quote(cell["row_key"])}, {quote(column)}, {quote(cell["value"])}')
        lines.append(f'get "modul4_registry_demo", {quote(found["child_id"])}')
    return '\n'.join(lines)+'\n'


def execute(script,text):
    return subprocess.run([sys.executable,str(ROOT/'code'/script)],input=text,
                          capture_output=True,text=True,encoding='utf-8',check=True).stdout


def run_mapreduce(folder,output_dir,node_count=3):
    children,_ = load(folder)
    lines = (Path(folder)/'children.tsv').read_text(encoding='utf-8').splitlines(keepends=True)
    chunks = [''.join(lines[::2]),''.join(lines[1::2])]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    application = YarnApplication(node_count=node_count)
    try:
        mapped_chunks = application.run_tasks([
            ('Mapper A',lambda:execute('registry_mapper.py',chunks[0])),
            ('Mapper B',lambda:execute('registry_mapper.py',chunks[1]))])
        mapped = ''.join(mapped_chunks)
        application.record('MapReduce','SHUFFLE_SORT','Group records by province|district after both maps complete')
        shuffled = ''.join(line+'\n' for line in sorted(mapped.splitlines(),key=lambda line:line.split('\t')[0]))
        reduced = application.run_tasks([('Reducer',lambda:execute('registry_reducer.py',shuffled))])[0]
        application.finish()
    except Exception:
        application.finish(False)
        raise
    finally:
        save_json(output_dir/'yarn.json',application.evidence())
    results = []
    for line in reduced.splitlines():
        key,n,d1,d3,coverage,dropout = line.split('\t')
        province,district = key.split('|')
        results.append({'province':province,'district':district,'eligible_children':int(n),
            'dose1_children':int(d1),'dose3_children':int(d3),'coverage_pct':float(coverage),
            'dropout_pct':None if dropout=='\\N' else float(dropout), 'missed_dose3':int(n)-int(d3)})
    expected = sql_coverage(children)
    keyed = lambda rows:{(row['province'],row['district']):row for row in rows}
    if keyed(results)!=keyed(expected):
        raise ValueError('Actual MapReduce output differs from SQL')
    for name,text in [('input-a.tsv',chunks[0]),('input-b.tsv',chunks[1]),
        ('map-a.tsv',mapped_chunks[0]),('map-b.tsv',mapped_chunks[1]),
        ('mapped.tsv',mapped),('shuffled.tsv',shuffled),('reduced.tsv',reduced)]:
        (output_dir/name).write_text(text,encoding='utf-8')
    result = {'runtime':'Resource-model scheduling of two Python mapper subprocesses, local sort and Python reducer',
        'synthetic':True,'source_rows':len(children),'cohort':COHORT,
        'mapper_input_rows':[len(chunk.splitlines()) for chunk in chunks],
        'mapper_output_rows':[len(chunk.splitlines()) for chunk in mapped_chunks],
        'selected_rows':len(mapped.splitlines()),'results':results,'matches_sql':True,
        'yarn':application.evidence(),'native_yarn':'NOT RUN'}
    save_json(output_dir/'results.json',result)
    return result


def print_coverage(rows,percentages=True,detail=False):
    if detail:
        print('Dihitung = anak yang memenuhi syarat. D1/D3 = sudah menerima dosis pertama/ketiga.')
    header = 'Provinsi / Kabupaten | Dihitung | D1 | D3'
    print(header+' | Cakupan D3 % | Putus lanjut %' if percentages else header)
    for row in rows:
        if not percentages:
            print(row['province'],row['district'],'|',row['eligible_children'],
                  '|',row['dose1_children'],'|',row['dose3_children'])
            continue
        dropout = 'N/A' if row['dropout_pct'] is None else f"{row['dropout_pct']:.2f}"
        print(row['province'],row['district'],'|',row['eligible_children'],'|',row['dose1_children'],
              '|',row['dose3_children'],'|',f"{row['coverage_pct']:.2f}",'|',dropout)


def storage(detail=False):
    children,events = load(DATA)
    metadata = json.loads((DATA/'metadata.json').read_text(encoding='utf-8'))
    if metadata.get('synthetic') is not True or any(digest(DATA/name)!=value for name,value in metadata['sha256'].items()):
        raise ValueError('Dummy data differs from metadata; run python code/prepare_dummy_dataset.py')
    runs = OUT/'runs'
    runs.mkdir(parents=True,exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d-%H%M%S-'),dir=runs))
    target = run/'storage'
    target.mkdir()
    names = ('children.csv','children.tsv','vaccination_events.csv','metadata.json')
    evidence = demonstrate_storage(DATA,names,run/'hdfs',target)
    for name in names:
        if digest(DATA/name)!=digest(target/name):
            raise ValueError('Storage copy hash mismatch')
    save_json(run/'session.json',{'run_id':run.name,'dataset_kind':'dummy-registry-v1',
        'created_utc':datetime.now(timezone.utc).isoformat(),'synthetic':True,
        'children':len(children),'vaccination_events':len(events),'cohort':COHORT,
        'storage_hashes':{name:digest(target/name) for name in names},'last_jobs':{},
        'runtime':'Python byte blocks, logical DataNodes, metadata and replica reads'})
    save_json(OUT/'latest.json',{'run_id':run.name,'dataset_kind':'dummy-registry-v1'})
    print('1. HDFS |',len(children),'anak |',len(events),'catatan dosis')
    print_storage(evidence,detail)
    if detail:
        print('Sesi:',run.name)
        for row in children[:3]:
            print(row['child_id'],row['province'],row['district'],row['birth_year'], 'D1/D2/D3:',row['dose1'],row['dose2'],row['dose3'])
    print('Hasil:',target.relative_to(ROOT))
    return run


def session():
    if not (OUT/'latest.json').exists():
        raise ValueError('Mulai dengan python code/demo.py storage')
    latest = json.loads((OUT/'latest.json').read_text(encoding='utf-8'))
    if latest.get('dataset_kind')!='dummy-registry-v1':
        raise ValueError('Sesi lama memakai WHO. Mulai sesi dummy dengan python code/demo.py storage')
    run = (OUT/'runs'/latest['run_id']).resolve()
    if not run.is_relative_to((OUT/'runs').resolve()) or run.name!=latest['run_id']:
        raise ValueError('Invalid session path')
    info = json.loads((run/'session.json').read_text(encoding='utf-8'))
    if any(digest(run/'storage'/name)!=value for name,value in info['storage_hashes'].items()):
        raise ValueError('Storage session changed; start a new storage session')
    if (run/'hdfs/namenode.json').exists():
        verify_storage(run/'hdfs',run/'storage')
    return run,info


def stage(name,child_id=DEFAULT_CHILD,yarn_nodes=3,detail=False,analysis='coverage',limit=5,province=None,district=None):
    if name not in STAGES:
        raise ValueError('Unknown demo stage')
    run,info = session()
    children,events = load(run/'storage')
    job = Path(tempfile.mkdtemp(prefix=name+'-',dir=run))
    if name=='mapreduce':
        print('2. MAPREDUCE + YARN | kohort',COHORT)
        if detail:
            print('Map = baca dan catat. Shuffle/sort = kelompokkan wilayah. Reduce = jumlahkan.')
        result = run_mapreduce(run/'storage',job,node_count=yarn_nodes)
        print_yarn(result['yarn'],detail)
        print('Alur data:',len(children),'anak ->',result['selected_rows'],'memenuhi syarat, lahir',COHORT,'->',len(result['results']),'kabupaten')
        for label,read_count,selected_count in zip(('A','B'),result['mapper_input_rows'],result['mapper_output_rows']):
            print('Mapper',label,': baca',read_count,'profil -> pilih',selected_count,'anak yang memenuhi syarat.')
        print_coverage(result['results'],percentages=False,detail=detail)
    elif name=='hive':
        print('3. HIVE | kohort',COHORT,'| analisis:',analysis)
        if detail:
            print('Cakupan = D3 / semua anak yang memenuhi syarat. Putus lanjut = (D1-D3) / D1.')
        rows = sql_coverage(children)
        reports = sql_analysis(children,limit)
        priority = [row for row in rows if row['coverage_pct']<80]
        result = {'runtime':'SQLite','synthetic':True,'cohort':COHORT,'results':rows,
                  'priority_rule':'coverage < 80%; invented teaching threshold, not outbreak prediction',
                  'priority_districts':priority,'native_hive':'NOT RUN',
                  'analysis':reports,'selected_analysis':analysis,'limit':limit}
        if info['last_jobs'].get('mapreduce'):
            mr = json.loads((run/info['last_jobs']['mapreduce']/'results.json').read_text(encoding='utf-8'))
            keyed = lambda values:{(row['province'],row['district']):row for row in values}
            if keyed(rows)!=keyed(mr['results']):
                raise ValueError('SQL differs from MapReduce in this session')
            result['matches_mapreduce'] = True
            if detail:
                print('Hasil SQL cocok dengan MapReduce sesi ini.')
        if analysis in ('coverage','all'):
            print_coverage(rows,detail=detail)
            print('Cakupan D3 < 80%:',len(priority),'kabupaten | N/A: D1 = 0')
            if detail:
                print('Kabupaten prioritas:',', '.join(row['district'] for row in priority))
                print('Batas 80% dipilih untuk latihan.')
        if analysis!='coverage':
            print_analysis(reports,analysis,limit,detail)
        write_csv(job/'coverage.csv',list(rows[0]),rows)
        write_csv(job/'priority_districts.csv',list(rows[0]),priority)
        (job/'query.sql').write_text((ROOT/'native/registry/coverage.sql').read_text(encoding='utf-8'),encoding='utf-8')
        for report_name,value in reports.items():
            records = [value] if report_name=='overall' else value
            fields = ([] if report_name=='overall' else ['province'] if report_name=='province' else ['province','district'])+ANALYSIS_FIELDS
            write_csv(job/f'{report_name}.csv',fields,records)
            query = (ROOT/f'native/registry/analysis_{report_name}.sql').read_text(encoding='utf-8')
            (job/f'query_{report_name}.sql').write_text(query.replace('LIMIT 5;',f'LIMIT {limit};'),encoding='utf-8')
    elif name=='pig':
        print('4. PIG | kohort',COHORT)
        cohort,missed,dropout,not_started = filter_followup(children,province,district)
        result = {'runtime':'Python filter/ETL','synthetic':True,'cohort':COHORT,
                  'source_rows':len(children),'cohort_rows':len(cohort),'missed_dose3':len(missed),
                  'dropout_children':len(dropout),'never_started_dose1':len(not_started),
                  'province':province,'district':district,'native_pig':'NOT RUN'}
        write_csv(job/'cohort.csv',FIELDS,cohort)
        write_csv(job/'missed_dose3.csv',FIELDS,missed)
        write_csv(job/'dropout_d1_d3.csv',FIELDS,dropout)
        write_csv(job/'not_started_d1.csv',FIELDS,not_started)
        if province:
            print('Wilayah dipilih:',province,district or '(semua kabupaten dalam dataset)')
        print(len(children),'anak ->',len(cohort),'memenuhi syarat, lahir',COHORT,'->',len(missed),'belum dosis ketiga')
        print('Belum D3:',len(missed),'= putus lanjut',len(dropout),'+ belum memulai D1',len(not_started))
        print('Contoh ID putus lanjut:',', '.join(row['child_id'] for row in dropout[:5]) or '(tidak ada)')
        if detail:
            print('Contoh ID belum D3:',', '.join(row['child_id'] for row in missed[:5]) or '(tidak ada)')
            print('File: cohort.csv, missed_dose3.csv, dropout_d1_d3.csv, not_started_d1.csv')
    else:
        print('5. HBASE | ID:',child_id)
        index = history_index(children,events)
        result = {'runtime':'Python dictionary keyed by child_id','synthetic':True,
                  'native_hbase':'NOT RUN',**lookup(children,events,child_id,index)}
        result['cells'] = column_cells(result)
        save_json(job/'history_index.json',index)
        write_csv(job/'column_cells.csv',['row_key','family','qualifier','value'],result['cells'])
        if result['found']:
            profile = result['profile']
            print(profile['province'],profile['district'],'| lahir:',profile['birth_date'])
            for event in result['history']:
                print('DTP'+str(event['dose_number']),event['vaccination_date'],event['facility_id'])
            if not result['history']:
                print('Riwayat dosis: kosong')
            print('Belum diterima (sudah waktunya):',', '.join(result['missing_due_doses']) or 'tidak ada')
            if detail:
                print('Row key = ID anak. Column family = kelompok kolom profile/history.')
                print('ID anak | kelompok:nama kolom | isi')
                for cell in result['cells']:
                    print(cell['row_key'],'|',cell['family']+':'+cell['qualifier'],'|',cell['value'])
            (job/'lookup.hbase').write_text(hbase_script(result),encoding='utf-8')
        else:
            print('ID tidak ditemukan.')
    save_json(job/'results.json',result)
    info['last_jobs'][name] = job.name
    save_json(run/'session.json',info)
    print('Hasil:',job.relative_to(ROOT))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['storage',*STAGES,'all'])
    parser.add_argument('--child',default=DEFAULT_CHILD,help='ID dummy for hbase lookup')
    parser.add_argument('--yarn-nodes',type=int,choices=(2,3),default=3,
                        help='Logical NodeManagers: 3 runs both maps concurrently; 2 shows the resource queue')
    parser.add_argument('--detail',action='store_true',help='Tampilkan rincian blok, log YARN, keterangan hasil dan kolom HBase')
    parser.add_argument('--analysis',choices=ANALYSES,default='coverage',help='Analisis Hive: coverage/highest/lowest/overall/province/all')
    parser.add_argument('--limit',type=int,default=5,help='Jumlah kabupaten dalam ranking Hive, 1 sampai 100; default 5')
    parser.add_argument('--province',help='Pilih provinsi untuk ETL Pig, misalnya Jawa Barat')
    parser.add_argument('--district',help='Pilih kabupaten untuk ETL Pig; isi --province juga')
    args = parser.parse_args()
    if not 1<=args.limit<=100:
        parser.error('--limit harus 1 sampai 100')
    if args.analysis!='coverage' and args.stage not in ('hive','all'):
        parser.error('--analysis digunakan pada tahap hive atau all')
    if (args.province or args.district) and args.stage!='pig':
        parser.error('--province dan --district digunakan pada tahap pig')
    if args.district and not args.province:
        parser.error('--district memerlukan --province')
    if args.stage in ('storage','all'):
        storage(args.detail)
    if args.stage=='all':
        for name in STAGES:
            stage(name,args.child,args.yarn_nodes,args.detail,args.analysis,args.limit)
    elif args.stage!='storage':
        stage(args.stage,args.child,args.yarn_nodes,args.detail,args.analysis,args.limit,args.province,args.district)


if __name__=='__main__':
    main()
