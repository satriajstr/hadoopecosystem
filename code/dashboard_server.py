"""Read-only local dashboard for completed demo stages; Python standard library."""
import argparse
import csv
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT/'output/manual-demo/runs'
LATEST = ROOT/'output/manual-demo/latest.json'
ASSETS = ROOT/'output/dashboard'
STAGES = ('storage','mapreduce','hive','pig','hbase')
DOWNLOADS = {'results.json','coverage.csv','overall.csv','highest.csv','lowest.csv',
             'province.csv','priority_districts.csv','cohort.csv','missed_dose3.csv',
             'dropout_d1_d3.csv','not_started_d1.csv','column_cells.csv','reduced.tsv'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def current_run_id(latest=LATEST):
    try:
        return read_json(latest).get('run_id')
    except (OSError, ValueError, AttributeError):
        return None


class DashboardState:
    def __init__(self, runs=RUNS, latest=LATEST, fresh=True):
        self.runs, self.latest = Path(runs).resolve(), Path(latest)
        self.baseline = current_run_id(self.latest) if fresh else None

    def run_folder(self, run_id):
        if not isinstance(run_id,str) or not run_id or Path(run_id).name!=run_id or '/' in run_id or '\\' in run_id:
            raise ValueError('Invalid session')
        folder = (self.runs/run_id).resolve()
        if folder.parent!=self.runs:
            raise ValueError('Session outside run directory')
        return folder

    def job_folder(self, run, stage, job_id):
        if not isinstance(job_id,str) or not job_id.startswith(stage+'-') or Path(job_id).name!=job_id:
            raise ValueError('Invalid completed job')
        folder = (run/job_id).resolve()
        if folder.parent!=run:
            raise ValueError('Job outside session')
        return folder

    def snapshot(self):
        empty = {'state':'empty','run':None,'stages':{s:{'status':'pending','data':None} for s in STAGES}}
        if not self.latest.exists():
            return {**empty,'message':'Belum ada sesi demo. Jalankan storage untuk mulai.'}
        try:
            latest = read_json(self.latest)
            run_id = latest['run_id']
            if run_id==self.baseline:
                return {**empty,'message':'Siap untuk demo baru. Jalankan storage di terminal.'}
            if latest.get('dataset_kind')!='dummy-registry-v1':
                raise ValueError('Sesi tidak memakai registri utama')
            run = self.run_folder(run_id)
            session = read_json(run/'session.json')
            if session.get('run_id')!=run_id:
                raise ValueError('Session identity mismatch')
            metadata = read_json(run/'storage/metadata.json')
            data = {**empty,'state':'ready','message':'Hasil sesi terbaru','run':{
                'id':run_id,'created_utc':session['created_utc'],
                'children':session['children'],'vaccination_events':session['vaccination_events'],
                'cohort':session['cohort'],'synthetic':session['synthetic'],
                'provinces':metadata['provinces'],'districts':metadata['districts'],
                'snapshot_date':metadata['snapshot_date']}}
            storage = read_json(run/'hdfs/results.json')
            files = [{'name':name,'blocks':len(f['blocks']),'bytes':f['bytes']}
                     for name,f in storage['initial']['files'].items()]
            data['stages']['storage'] = {'status':'ready','job':'storage','data':{
                'files':files,'blocks':sum(f['blocks'] for f in files),
                'replication':storage['initial']['replication'],
                'block_size_bytes':storage['initial']['block_size_bytes'],
                'failed_node':storage['failed_node'],'repairs':len(storage['repairs']),
                'hash_matches':storage['all_files_match_after_failure'],
                'replication_restored':storage['replication_restored']}}
            for stage in STAGES[1:]:
                job_id = session.get('last_jobs',{}).get(stage)
                if not job_id:
                    continue
                try:
                    folder = self.job_folder(run,stage,job_id)
                    result = read_json(folder/'results.json')
                    if stage=='mapreduce':
                        yarn = result['yarn']
                        result = {k:result[k] for k in ('cohort','source_rows','selected_rows',
                            'mapper_input_rows','mapper_output_rows','results','matches_sql')}
                        result['yarn'] = {'status':yarn['final_status'],
                            'queued':any(e['event']=='WAITING' for e in yarn['events']),
                            'resource_released':all(n['used_cpu']==0 and n['used_memory_mb']==0 for n in yarn['nodes'].values()),
                            'tasks':[{'task':c['task'],'node':c['node']} for c in yarn['containers'].values()]}
                    elif stage=='pig':
                        result['preview'] = {}
                        for name in ('dropout_d1_d3','not_started_d1','missed_dose3'):
                            with (folder/(name+'.csv')).open(encoding='utf-8',newline='') as stream:
                                reader = csv.DictReader(stream)
                                preview=[]
                                for row in reader:
                                    preview.append(row)
                                    if len(preview)==12:
                                        break
                            result['preview'][name] = preview
                    elif stage=='hbase':
                        result = {k:result[k] for k in ('child_id','found','profile','history','missing_due_doses')}
                    artifacts = {p.name:'/results/'+quote(run_id)+'/'+quote(job_id)+'/'+quote(p.name)
                                 for p in folder.iterdir() if p.is_file() and p.name in DOWNLOADS}
                    data['stages'][stage] = {'status':'ready','job':job_id,
                        'updated_utc':datetime.fromtimestamp((folder/'results.json').stat().st_mtime,timezone.utc).isoformat(),
                        'artifacts':artifacts,'data':result}
                except (OSError, ValueError, KeyError, TypeError):
                    data['stages'][stage] = {'status':'waiting','data':None,'message':'Hasil sedang diperbarui.'}
            if current_run_id(self.latest)!=run_id:
                return {**empty,'state':'waiting','message':'Pergantian sesi. Menunggu hasil baru.'}
            return data
        except FileNotFoundError:
            return {**empty,'state':'waiting','message':'Sesi sedang disiapkan atau telah dibersihkan.'}
        except (OSError,ValueError,KeyError,TypeError):
            return {**empty,'state':'waiting','message':'Menunggu berkas sesi selesai diperbarui.'}

    def download(self, path):
        parts = unquote(path).split('/')
        if len(parts)!=5 or parts[1]!='results' or parts[4] not in DOWNLOADS:
            raise ValueError('Unknown artifact')
        _,_,run_id,job_id,name = parts
        latest = read_json(self.latest)
        if run_id!=latest.get('run_id') or run_id==self.baseline:
            raise ValueError('Artifact is not in the visible session')
        run = self.run_folder(run_id)
        session = read_json(run/'session.json')
        stage = next((s for s,j in session['last_jobs'].items() if j==job_id),None)
        if stage not in STAGES[1:]:
            raise ValueError('Uncommitted job')
        job = self.job_folder(run,stage,job_id)
        file = (job/name).resolve()
        if file.parent!=job:
            raise ValueError('Artifact outside job')
        return file


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path=='/api/dashboard':
                body = json.dumps(self.server.state.snapshot(),ensure_ascii=False).encode('utf-8')
                return self.respond(body,'application/json; charset=utf-8')
            if path.startswith('/results/'):
                file = self.server.state.download(path)
                return self.respond(file.read_bytes(),'application/octet-stream',attachment=file.name)
            assets = {'/':'index.html','/index.html':'index.html',
                      '/dashboard.css':'dashboard.css','/dashboard.js':'dashboard.js'}
            assets.update({'/fonts/'+name:'fonts/'+name for name in (
                'Poppins-Regular.ttf','Poppins-Medium.ttf','Poppins-SemiBold.ttf','Poppins-Bold.ttf')})
            if path not in assets:
                self.send_error(404)
                return
            file = ASSETS/assets[path]
            mime = {'html':'text/html','css':'text/css','js':'text/javascript','ttf':'font/ttf'}[file.suffix[1:]]
            self.respond(file.read_bytes(),mime if file.suffix=='.ttf' else mime+'; charset=utf-8')
        except (OSError,ValueError,KeyError,TypeError):
            self.send_error(404)

    def respond(self, body, mime, attachment=None):
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if attachment:
            self.send_header('Content-Disposition','attachment; filename="'+attachment+'"')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--resume',action='store_true',help='Tampilkan hasil sesi terakhir saat server dimulai')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.state = DashboardState(fresh=not args.resume)
    print(f'Dashboard: http://127.0.0.1:{server.server_port}',flush=True)
    print('Mode: '+('sesi terakhir' if args.resume else 'kosong; jalankan storage baru'),flush=True)
    print('Biarkan terminal ini terbuka. Ctrl+C untuk berhenti.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=='__main__':
    main()
