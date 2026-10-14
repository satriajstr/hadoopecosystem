"""Build an offline companion to four manual Windows demo stages.

All calculated results come from Python/SQLite. Native code is prepared only.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from manual_who_demo import FIELDS, load_tsv, sql_results, filter_group, write_csv
from immunization_mapper import COUNTRIES, YEARS
from run_immunization_mapreduce import main as prepare_case_mapreduce

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/who-presentation'
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return (ROOT/path).read_text(encoding='utf-8')


def table(headers, rows):
    head = ''.join('<th>'+html.escape(str(v))+'</th>' for v in headers)
    body = ''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)
    return '<div class="table-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def code(text):
    return '<pre><code>'+html.escape(text.strip())+'</code></pre>'


def source_block(label, text):
    return '<details><summary>'+html.escape(label)+'</summary>'+code(text)+'</details>'


def flow(items):
    return '<div class="flow">'+''.join('<div>'+html.escape(v)+'</div>' for v in items)+'</div>'


def pct(value):
    return '—' if value is None else f'{float(value):g}%'.replace('.', ',')


def command(stage):
    return code('python code/manual_who_demo.py '+stage)


def section(id_, number, title, content):
    return '<section id="'+id_+'"><div class="eyebrow">'+number+'</div><h2>'+title+'</h2>'+content+'</section>'


input_path = ROOT/'data/real/immunization_coverage_long.tsv'
records = load_tsv(input_path)
queries = sql_results(input_path)
selected, counts = filter_group(input_path)
case_mr = prepare_case_mapreduce()
means = queries[2]['rows']
assert queries[0]['rows'] == [(20032,)]
assert {row[0]:(int(row[5]),float(row[6])) for row in means} == {
    row['area_code']:(row['year_count'],float(row['mean_yearly_coverage_pct'])) for row in case_mr['results']}
assert len(selected)==60 and len(counts)==30 and all(row[2]==2 for row in counts)
assert len(queries)==5 and len(queries[4]['rows'])==30
write_csv(OUT/'filtered_countries.csv',FIELDS,([row[key] for key in FIELDS] for row in selected))
write_csv(OUT/'grouped_country_year.csv',['area_code','year','indicator_rows'],counts)
write_csv(OUT/'dtp3_means.csv',queries[2]['columns'],means)
write_csv(OUT/'coverage_dropout.csv',queries[4]['columns'],queries[4]['rows'])
provenance = json.loads(read('source/real/provenance.json'))
raw = ROOT/'source/real/unicef_dtp1_dtp3_1980_2025.json'
assert hashlib.sha256(raw.read_bytes()).hexdigest()==provenance['raw_sha256']
word_input = read('data/sample.txt')
word_output = [line.split('\t') for line in read('output/wordcount.tsv').splitlines()]
assert {word:int(count) for word,count in word_output}==dict(Counter(word_input.split()))

badge = '<span class="badge local">Pelengkap · data WHO/UNICEF</span>'
pages = []
pages.append('<section id="intro"><div class="eyebrow">MODUL 4 · HADOOP ECOSYSTEM</div>'
    '<h1>Demo imunisasi lima negara</h1><p class="lead">Indonesia, Malaysia, Thailand, Viet Nam, dan Philippines. '
    'Empat tahap dijalankan manual melalui terminal Windows; halaman ini menampilkan alur dan hasil pembanding.</p>'
    '<div class="metrics"><div><strong>20.032</strong><span>observasi input internasional</span></div>'
    '<div><strong>5 negara</strong><span>fokus analisis 2020–2025</span></div>'
    '<div><strong>4 tahap</strong><span>Python/SQLite tanpa VM</span></div></div>'+
    flow(['Storage lokal','MapReduce Python','Query SQLite','Filter/group Python'])+
    table(['Agenda modul','Runtime demo manual','Perintah'],[
        ('HDFS / storage','Salin, lihat, dan baca file lokal','python code/manual_who_demo.py storage'),
        ('MapReduce + YARN','Dua mapper Python, sort lokal, reducer Python','python code/manual_who_demo.py mapreduce'),
        ('Hive / analisis','SQLite menjalankan lima query','python code/manual_who_demo.py hive'),
        ('Pig / transformasi','Filter dan group dengan Python','python code/manual_who_demo.py pig')])+
    '<p>Ikuti alur dari dataset internasional lengkap hingga hasil per negara. '
    'Storage, pemrosesan, query, dan transformasi memiliki peran yang berbeda dalam pipeline.</p>'
    '<p>Sumber tetap dataset internasional lengkap. Lima negara dipilih saat pemrosesan, bukan dipangkas sebelum tahap storage.</p>'
    '<p class="source">Sumber: <a href="'+html.escape(provenance['source_page'],quote=True)+'">WHO/UNICEF WUENIC via UNICEF</a> '
    '· revisi 2025 · agregat wilayah/kelompok dan tahun, bukan rekam anak.</p></section>')

pages.append(section('storage','01 · STORAGE LOKAL / KONSEP HDFS','Simpan input internasional lengkap',
    badge+'<p class="lead">Satu file TSV berisi 20.032 observasi, '+str(input_path.stat().st_size)+' byte. '
    'Tahap ini membuat sesi baru dan menyalin dataset ke folder storage sesi tersebut.</p>'+command('storage')+
    flow(['Snapshot API SDMX','Konversi CSV/TSV','Salin semua wilayah','Periksa SHA-256 + cuplikan'])+
    '<div class="split"><div class="card"><h3>Cuplikan sumber internasional</h3>'+
    table(['Wilayah','Tahun','Indikator','Cakupan'],[(r['area_code'],r['year'],r['indicator'],pct(r['coverage_pct'])) for r in records[:5]])+
    '<p>File sumber dan salinan harus memiliki hash yang sama. Tidak ada pemilihan Indonesia atau lima negara pada tahap storage.</p></div>'
    '<div class="card"><h3>Padanan di HDFS</h3>'+code('hdfs dfs -mkdir -p "$HDFS_BASE/analytics"\n'
        'hdfs dfs -put data/real/immunization_coverage_long.tsv "$HDFS_BASE/analytics/coverage.tsv"\n'
        'hdfs dfs -ls "$HDFS_BASE/analytics"\nhdfs dfs -head "$HDFS_BASE/analytics/coverage.tsv"')+
    '<p>NameNode mengelola metadata; DataNode menyimpan blok. '
    'Salinan Windows saat ini berada di filesystem lokal.</p></div></div>'+
    '<p class="note">296 kode wilayah/kelompok pada sumber tidak berarti 296 negara. Mengunggah ke HDFS menyimpan data; '
    'penyaringan isi dilakukan pada tahap pengolahan.</p>'))

trend = {(r['area_code'],r['year']):r['coverage_pct'] for r in case_mr['input']}
pages.append(section('case-mapreduce','02 · MAPREDUCE PYTHON / PERAN YARN','Rata-rata DTP3 per negara',
    badge+'<p class="lead">Hitung rata-rata sederhana enam estimasi tahunan DTP3 untuk setiap negara.</p>'+command('mapreduce')+
    flow(['20.032 baris → 2 mapper','Map memilih 30 DTP3','Sort key per negara','Reduce → 5 hasil'])+
    table(['Tahun']+list(COUNTRIES),[[year]+[pct(trend[country,year]) for country in COUNTRIES] for year in YEARS])+
    '<div class="split"><div class="card"><h3>Map dan shuffle yang dieksekusi</h3>'+
    table(['Proses Python','Input global','Pasangan DTP3 terpilih'],[
        ('Mapper A',case_mr['mapper_input_rows'][0],case_mr['mapper_output_rows'][0]),
        ('Mapper B',case_mr['mapper_input_rows'][1],case_mr['mapper_output_rows'][1])])+
    code('Key ringkas: IDN / DTP3\nValue: (cakupan, 1)\n'
         'Shuffle IDN: (77,1), (67,1), (91,1), (83,1), (78,1), (82,1)\n'
         'Reduce IDN: 478 / 6 = 79,67%')+
    '<p>Key lengkap memuat negara, indikator, sex, unit, status, revisi, dan kelompok umur. '
    'Malaysia dan negara lain memiliki key sendiri sehingga hasil tidak tercampur.</p></div>'
    '<div class="card"><h3>Output reducer aktual</h3>'+
    table(['Negara','Sum persentase tahunan','Tahun','Mean DTP3'],[
        (r['area_name'],r['sum_of_year_percentages'],r['year_count'],pct(r['mean_yearly_coverage_pct'])) for r in case_mr['results']])+
    '<p>Sum hanya dipakai sebagai pembilang rata-rata. Setiap tahun berbobot sama; '
    'hasil ini bukan cakupan gabungan populasi bayi dan bukan rata-rata global.</p></div></div>'+
    '<div class="card"><h3>Peran YARN pada Hadoop</h3><p>YARN mengalokasikan CPU/RAM untuk ApplicationMaster '
    'dan container tugas. Framework MapReduce menangani pembagian input, shuffle/sort, dan reducer. '
    'Alur pemrosesan meliputi dua mapper, pengelompokan key, dan reducer. '
    'YARN menyediakan resource yang dibutuhkan job.</p></div>'+
    source_block('Kode mapper imunisasi',read('code/immunization_mapper.py'))+
    source_block('Kode reducer imunisasi',read('code/immunization_reducer.py'))+
    source_block('Kode submit Hadoop/YARN yang disiapkan',read('native/demo/02_immunization.sh'))))

latest = [row for row in queries[4]['rows'] if row[2]==2025]
pages.append(section('analytics','03 · SQLITE / QUERY PEMBANDING HIVE','Analisis dan pemeriksaan silang',
    badge+'<p class="lead">SQLite memuat input internasional yang sama. Lima query menghitung jumlah observasi, '
    'cakupan terbaru, mean DTP3, tren, dan proxy dropout agregat.</p>'+command('hive')+
    flow(['20.032 baris dalam tabel','WHERE lima negara','SQL agregasi / pasangan','Cocokkan mean dengan reducer'])+
    '<h3>DTP1/DTP3 dan proxy dropout tahun 2025</h3>'+
    table(['Negara','DTP1','DTP3','Selisih (pp)','Proxy dropout'],[
        (name,pct(d1),pct(d3),f'{gap:g}',pct(proxy)) for _,name,_,d1,d3,gap,proxy in latest])+
    '<div class="split"><div class="card"><h3>Query mean yang benar-benar dihitung</h3>'+code(queries[2]['sql'])+
    '</div><div class="card"><h3>Interpretasi Indonesia 2025</h3>'+code('(85 - 82) / 85 * 100 = 3,53%')+
    '<p>DTP3 lebih rendah tiga poin persentase daripada DTP1. Proxy ini memakai dua estimasi agregat; '
    'tidak melacak anak yang sama. Mean DTP3 2020–2025 tetap 79,67%, berbeda dari cakupan 2025 sebesar 82%.</p>'
    '<p>Mean dan jumlah tahun untuk kelima negara cocok dengan hasil MapReduce lokal. '
    'Perintah manual memeriksa kesamaan ini apabila MapReduce sudah dijalankan dalam sesi tersebut.</p></div></div>'+
    source_block('Lima query lengkap',read('native/demo/hive_walkthrough.sql'))+
    '<p>External table memberi struktur pada file, lalu SQL memilih dan meringkas data sesuai pertanyaan analisis.</p>'))

pages.append(section('etl','04 · FILTER/GROUP PYTHON / PEMBANDING PIG','Pilih dan kelompokkan dua indikator',
    badge+'<p class="lead">Pilih lima negara, 2020–2025, DTP1 dan DTP3, lalu hitung observasi per negara–tahun.</p>'+command('pig')+
    flow(['LOAD: 20.032 baris','FILTER: 60 observasi','GROUP: 30 negara–tahun','STORE: dua CSV'])+
    table(['Negara','Tahun','Observasi DTP1+DTP3'],[(COUNTRIES[country],year,count) for country,year,count in counts])+
    '<p>Setiap kelompok berisi dua baris indikator, bukan dua anak atau dua dosis individual. '
    'Nilai cakupan dan metadata sumber tetap dipertahankan pada hasil filter.</p>'+
    source_block('Kode Pig Latin yang disiapkan',read('native/demo/real_filter_group.pig'))+
    '<p>Pig Latin mengekspresikan urutan LOAD, FILTER, GROUP, dan STORE.</p>'))

pages.append(section('wordcount','CADANGAN · WORD COUNT PYTHON','Latihan dasar map dan reduce',
    badge+'<p>Contoh teks kecil dari modul tetap tersedia sebagai tambahan. Demo utama memakai data imunisasi resmi.</p>'+
    '<div class="split"><div class="card"><h3>Input</h3>'+code(word_input)+
    '<h3>Pasangan setelah sort</h3>'+code(read('output/shuffled.tsv'))+'</div>'+
    '<div class="card"><h3>Output reducer lokal</h3>'+table(['Kata','Jumlah'],word_output)+
    source_block('Kode mapper Word Count',read('code/mapper.py'))+
    source_block('Kode reducer Word Count',read('code/reducer.py'))+'</div></div>'))

pages.append(section('close','PENUTUP · PENGULANGAN DEMO','Ulangi tanpa menimpa percobaan sebelumnya',
    '<p>Jalankan empat perintah sesuai urutan. Setiap storage membuat sesi baru. '
    'MapReduce, SQL, dan filter/group dapat diulang pada sesi yang sama; masing-masing menulis folder percobaan baru.</p>'+
    code('python code/manual_who_demo.py storage\npython code/manual_who_demo.py mapreduce\n'
         'python code/manual_who_demo.py hive\npython code/manual_who_demo.py pig')+
    '<p>Hasil tersimpan di <code>output/manual-who/runs/</code>. '
    '<code>latest.json</code> menunjuk sesi aktif, dan <code>session.json</code> mencatat percobaan terakhir. '
    'Halaman ini adalah hasil pembanding yang disiapkan; perintah dijalankan melalui terminal.</p>'+
    table(['Komponen modul','Yang diperlihatkan'],[
        ('HDFS','Konsep storage; salinan dan pembacaan file Windows'),
        ('MapReduce / YARN','Map, sort, reduce Python; peran resource YARN dijelaskan'),
        ('Hive','Hasil query SQLite atas data resmi'),
        ('Pig','Hasil filter/group Python')])+
    '<p class="note">Dataset ini mendukung analisis cakupan nasional dan perbandingan antarnegara. '
    'Tidak memiliki data provinsi, identitas anak, atau riwayat individual untuk HBase. '
    'Ukuran sekitar 2,5 MB juga tidak membuktikan Volume/Velocity skala big data atau performa cluster.</p>'+
    '<div class="sources"><h3>Panduan dan hasil pembanding</h3><ul>'
    '<li><a href="../../DEMO_MANUAL_WHO_WINDOWS.md">Panduan demo manual Windows</a></li>'
    '<li><a href="dtp3_means.csv">Lima hasil mean DTP3</a></li>'
    '<li><a href="coverage_dropout.csv">Cakupan dan proxy dropout 2020–2025</a></li>'
    '<li><a href="filtered_countries.csv">60 observasi hasil filter</a></li>'
    '<li><a href="grouped_country_year.csv">30 kelompok negara–tahun</a></li>'
    '<li><a href="evidence.json">Runtime, query, dan hash sumber</a></li></ul></div>'))

style = '''
:root{--ink:#152c45;--muted:#51647a;--line:#d8e2ec;--blue:#1166a8;--bg:#f3f7fa}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.6 "Segoe UI",Arial,sans-serif}header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);z-index:5;padding:12px 4vw;display:flex;justify-content:space-between;align-items:center;gap:16px}header strong{font-size:18px}nav{display:flex;gap:6px;flex-wrap:wrap}nav a{font-size:14px;color:var(--muted);text-decoration:none;padding:6px 10px;border-radius:6px}nav a:hover,nav a.active{background:#e4f0fa;color:var(--blue)}main{max-width:1320px;margin:auto;padding:0 4vw}section{padding:42px 0 50px;scroll-margin-top:80px;border-bottom:1px solid var(--line)}h1{font-size:clamp(34px,4vw,54px);line-height:1.15;margin:15px 0}h2{font-size:clamp(28px,3vw,40px);line-height:1.25;margin:10px 0 16px}h3{font-size:20px;margin:0 0 12px}.eyebrow{color:var(--blue);font-weight:700;font-size:13px;letter-spacing:1.7px}.lead{font-size:21px;max-width:1000px;color:var(--muted)}.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700}.local{background:#ddf2e8;color:#176441}.design{background:#fff0d9;color:#825510}.split{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:22px 0}.card{padding:22px;border:1px solid var(--line);border-radius:12px;background:#fff;min-width:0}.card p{font-size:16px}.card .split{gap:12px;margin:8px 0}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:28px 0}.metrics div{background:#fff;border-left:4px solid var(--blue);padding:20px;border-radius:4px}.metrics strong{display:block;font-size:36px;line-height:1.3}.metrics span{color:var(--muted);font-size:15px}.flow{display:flex;gap:10px;align-items:stretch;margin:24px 0}.flow div{flex:1;background:#e7f0f8;padding:14px;border-radius:6px;position:relative;font-size:16px;font-weight:600}.flow div+div::before{content:"→";position:absolute;left:-14px;top:14px;color:var(--blue);font-size:19px}.note{background:#fff8e9;border-left:4px solid #d2a344;padding:14px 18px;font-size:16px}.source{font-size:14px;color:var(--muted)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff;font-size:17px}th,td{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line)}th{background:#e7f0f8;font-size:14px}pre{background:#13293d;color:#e5f0fa;padding:16px;border-radius:8px;overflow:auto;font:14px/1.6 Consolas,monospace;tab-size:4}details{margin:12px 0;border:1px solid var(--line);border-radius:8px;padding:10px 14px;background:#fff}summary{cursor:pointer;color:var(--blue);font-size:15px;font-weight:600}a{color:var(--blue)}blockquote{font-size:22px;border-left:4px solid var(--blue);margin:25px 0;padding:10px 22px;background:#e7f0f8}.sources{font-size:15px}.sources li{margin:5px 0}footer{font-size:13px;color:var(--muted);padding:22px 4vw}ol{padding-left:22px;font-size:17px}button{border:1px solid var(--line);background:white;border-radius:6px;padding:7px 10px;color:var(--blue);cursor:pointer}@media(max-width:760px){header{position:static;display:block}.split,.metrics{grid-template-columns:1fr}.flow{flex-wrap:wrap}.flow div{min-width:40%}.flow div+div::before{content:""}section{padding:30px 0}}@media print{header,details{display:none}section{break-before:page;border:0;padding:15px 0}.card,table,.note{break-inside:avoid}body{font-size:14px}main{padding:0}.lead{font-size:17px}pre{white-space:pre-wrap}.metrics strong{font-size:26px}}
'''

nav = ''.join(f'<a href="#{id_}">{label}</a>' for id_,label in [
    ('intro','Mulai'),('storage','Storage / HDFS'),('case-mapreduce','MapReduce / YARN'),
    ('analytics','SQL / Hive'),('etl','Filter / Pig'),('wordcount','Word Count'),('close','Ulangi')])
page = ('<!doctype html><html lang="id"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Modul 4 — Demo Manual Lima Negara</title><style>'+style+'</style></head><body>'
    '<header><strong>Hadoop Ecosystem · Modul 4</strong><nav>'+nav+'</nav></header><main>'+''.join(pages)+'</main>'
    '<footer>Modul 4 · alur Hadoop Ecosystem · pelengkap WHO/UNICEF</footer>'
    '<script>const sections=[...document.querySelectorAll("section")];'
    'const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){'
    'document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("active",a.hash==="#"+entry.target.id));}}},'
    '{rootMargin:"-20% 0px -55% 0px"});sections.forEach(s=>observer.observe(s));</script></body></html>')
(OUT/'index.html').write_text(page,encoding='utf-8')
evidence = {'built_utc':datetime.now(timezone.utc).isoformat(), 'source_snapshot':provenance,
    'countries':COUNTRIES,'years':list(YEARS),'source_input_rows':len(records),
    'storage_runtime':'Windows filesystem copy; no HDFS',
    'sql_runtime':'SQLite; five statements in native/demo/hive_walkthrough.sql',
    'sql_results':queries,'filter_group_runtime':'Python; prepared Pig predicate',
    'filtered_rows':len(selected),'grouped_rows':counts,'immunization_mapreduce':case_mr,
    'wordcount_runtime':'Python subprocesses and local sort',
    'native_execution':{key:'NOT RUN' for key in ('HDFS','YARN','Hive','Pig')}}
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding='utf-8')
print('Created:',OUT/'index.html')
print('Verified: five-country SQL/MapReduce match; 60 filtered observations; 30 groups; source hash; Word Count.')
print('WHO companion presentation updated.')
