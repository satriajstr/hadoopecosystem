"""Offline presentation for the manual fictional child registry demo."""
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from prepare_dummy_dataset import ROOT, DATA, FIELDS, COHORT, DEFAULT_CHILD, load, digest, write_csv, save_json
from demo import sql_coverage, filter_cohort, lookup, column_cells, hbase_script, run_mapreduce, sql_analysis, filter_followup
from concept_storage import demonstrate_storage

OUT = ROOT/'output/presentation'
OUT.mkdir(parents=True,exist_ok=True)


def read(path):
    return (ROOT/path).read_text(encoding='utf-8')


def code(text):
    return '<pre><code>'+html.escape(text.strip())+'</code></pre>'


def source_block(label,text):
    return '<details><summary>'+html.escape(label)+'</summary>'+code(text)+'</details>'


def table(headers,rows):
    head = ''.join('<th>'+html.escape(str(v))+'</th>' for v in headers)
    body = ''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)
    return '<div class="table-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def flow(items):
    return '<div class="flow">'+''.join('<div>'+html.escape(v)+'</div>' for v in items)+'</div>'


def section(id_,label,title,content):
    return '<section id="'+id_+'"><div class="eyebrow">'+label+'</div><h2>'+title+'</h2>'+content+'</section>'


def pct(value):
    return 'N/A (D1 = 0)' if value is None else f'{float(value):.2f}%'.replace('.',',')


def command(stage):
    return code('python code/demo.py '+stage)


children,events = load()
metadata = json.loads(read('data/dummy/metadata.json'))
assert metadata['synthetic'] is True
assert all(digest(DATA/name)==value for name,value in metadata['sha256'].items())
coverage = sql_coverage(children)
analysis = sql_analysis(children)
cohort,missed = filter_cohort(children)
_,_,dropout,not_started = filter_followup(children)
storage = demonstrate_storage(DATA,('children.csv','children.tsv','vaccination_events.csv','metadata.json'),
    OUT/'registry-storage/hdfs',OUT/'registry-storage/snapshot')
mr = run_mapreduce(DATA,OUT/'registry-mapreduce')
history = lookup(children,events,DEFAULT_CHILD)
cells = column_cells(history)
assert len(children)==metadata['children'] and len(events)==metadata['vaccination_events']
assert mr['matches_sql'] is True and len(mr['results'])==metadata['districts']
assert history['found'] and history['missing_due_doses']==['DTP3']
priority = [row for row in coverage if row['coverage_pct']<80]
utara = next(row for row in coverage if row['district']=='Kabupaten Bandung')
blocks = sum(len(info['blocks']) for info in storage['initial']['files'].values())
empty_child = next(row['child_id'] for row in children if row['dose3_due'] and row['dose1']==0)


def n(value):
    return f'{value:,}'.replace(',','.')
write_csv(OUT/'registry_coverage.csv',list(coverage[0]),coverage)
write_csv(OUT/'registry_priority.csv',list(coverage[0]),priority)
write_csv(OUT/'registry_cohort.csv',FIELDS,cohort)
write_csv(OUT/'registry_missed_dose3.csv',FIELDS,missed)
save_json(OUT/'registry_lookup.json',history)
save_json(OUT/'registry_analysis.json',analysis)
write_csv(OUT/'registry_dropout_d1_d3.csv',FIELDS,dropout)
write_csv(OUT/'registry_not_started_d1.csv',FIELDS,not_started)
write_csv(OUT/'registry_column_cells.csv',['row_key','family','qualifier','value'],cells)
(ROOT/'native/registry/lookup.hbase').write_text(hbase_script(history),encoding='utf-8')


def action(stage,purpose,watch):
    return ('<div class="action"><h3>Coba di terminal</h3><p>'+purpose+
            ' Ketik perintah berikut di PowerShell, lalu tekan <strong>Enter</strong>.</p>'+
            command(stage)+'<p><strong>Perhatikan hasilnya:</strong> '+watch+'</p></div>')


def say(text):
    return '<blockquote><strong>Kalimat untuk presentasi:</strong> “'+text+'”</blockquote>'


def next_step(text):
    return '<p class="next-step"><strong>Setelah ini:</strong> '+text+'</p>'


badge = '<span class="badge local">Contoh: catatan imunisasi anak</span>'
pages = []
pages.append('<section id="intro"><div class="eyebrow">MODUL 4 · HADOOP ECOSYSTEM</div>'
    '<h1>Bagaimana data imunisasi diolah?</h1>'
    '<p class="lead">Bayangkan catatan imunisasi dari beberapa provinsi dikumpulkan. '
    'Kita ingin tahu: kabupaten mana yang masih banyak anak belum menerima dosis ketiga, '
    'dan siapa saja anaknya?</p>'
    '<p>Kita memakai data buatan agar prosesnya mudah diikuti. Setiap alat memiliki tugas berbeda: '
    'menyimpan, membagi pekerjaan, menghitung, menyaring, atau mencari catatan seorang anak.</p>'
    '<p class="note"><strong>Data imunisasi sintetis untuk pembelajaran, menggunakan nama wilayah asli Indonesia.</strong> Angka pada halaman ini bukan kondisi imunisasi sebenarnya di daerah tersebut.</p>'
    f'<div class="metrics"><div><strong>{n(len(children))}</strong><span>anak dalam data contoh</span></div>'
    f'<div><strong>{metadata["provinces"]} / {metadata["districts"]}</strong><span>provinsi / kabupaten Indonesia</span></div>'
    f'<div><strong>{n(len(events))}</strong><span>catatan pemberian dosis</span></div></div>'+
    '<h3>Kenali datanya dahulu</h3>'+
    table(['Istilah yang akan muncul','Arti sederhana'],[
        ('Profil anak','Satu baris berisi ID, wilayah, tahun lahir, dan status dosis seorang anak'),
        ('Catatan dosis','Satu baris untuk satu pemberian dosis. Seorang anak bisa memiliki beberapa catatan'),
        ('D1, D2, D3','Dosis pertama, kedua, dan ketiga vaksin DTP. Angka 1 = sudah menerima; 0 = belum menerima'),
        ('Kelompok analisis','Anak kelahiran 2023 yang dalam data contoh sudah ditandai waktunya menerima D3'),
        ('Kohort / eligible','Kohort = kelompok tahun lahir yang sama. Eligible = memenuhi syarat untuk dihitung')])+
    '<p>Contoh: anak dengan D1=1, D2=1, D3=0 sudah menerima dosis pertama dan kedua, tetapi belum dosis ketiga. '
    f'Dari {n(len(children))} anak, ada {n(len(cohort))} yang masuk kelompok analisis kita. Penanda waktunya menerima D3 '
    '(<code>dose3_due</code>) dibuat untuk latihan, bukan aturan jadwal klinis.</p>'+
    '<h3>Urutan yang akan kita lihat</h3>'+table(['Tahap','Pertanyaan yang dijawab'],[
        ('1. HDFS — menyimpan data','Bagaimana file dibagi dan tetap terbaca saat satu tempat penyimpanan gagal?'),
        ('2. MapReduce + YARN — menghitung bersama','Bagaimana pekerjaan dibagi dan kapasitas komputer diatur?'),
        ('3. Hive — membaca hasil dengan SQL','Berapa cakupan imunisasi dan putus lanjut dosis di tiap kabupaten?'),
        ('4. Pig — memilih data','Anak mana yang masuk kelompok analisis dan belum menerima D3?'),
        ('5. HBase — mencari satu anak','Bagaimana riwayat imunisasi anak yang dipilih dari daftar tadi?')])+
    '<p>Urutan ini membantu kita bercerita. Analisis, penyaringan, dan pencarian memakai sumber data yang sama; '
    'hasil penyaringan memberi ID anak yang dapat dicari riwayatnya.</p>'+
    '<h3>Sebelum mengetik perintah</h3><ol>'
    '<li>Buka <strong>PowerShell</strong>: tempat mengetik perintah untuk menjalankan demo.</li>'
    '<li>Masuk ke folder proyek dengan perintah di bawah. Ini hanya memilih folder kerja.</li>'
    '<li>Baca penjelasan tiap tahap, kemudian jalankan satu perintah pada bagian “Coba di terminal”.</li></ol>'+
    code("Set-Location 'C:\Kuliah\Semester 5\Big Data\HadoopEcosystem'")+
    '<p>Contoh bentuk perintah: <code>python code/demo.py storage</code>. '
    '<code>python</code> menjalankan program; <code>code/demo.py</code> adalah file demo; '
    '<code>storage</code> memilih tahap penyimpanan. Bagian terakhir berubah sesuai tahap.</p>'+
    '<p>Halaman ini berisi contoh hasil untuk dibaca. Hasil percobaan yang baru kamu jalankan muncul di terminal '
    'dan disimpan dalam folder yang disebutkan di akhir proses.</p>'+
    '<details><summary>Alat pendukung lain dalam modul</summary><p>Alat ini membantu data masuk dan mengatur urutan pekerjaan.</p>'+
    table(['Alat','Arti perannya'],[
        ('Sqoop','Memindahkan data dalam satu kumpulan dari database ke Hadoop atau sebaliknya'),
        ('Flume','Mengumpulkan catatan kejadian/log, menampungnya, lalu mengirimkannya ke penyimpanan'),
        ('Oozie','Menjalankan urutan pekerjaan: pekerjaan berikutnya menunggu pekerjaan sebelumnya berhasil')])+'</details>'+
    next_step('mulai dari penyimpanan seluruh data pada tahap HDFS.')+'</section>')

pages.append(section('storage','01 · HDFS','Simpan data dan buat salinan cadangan',
    badge+'<p class="lead">Sebelum menghitung, kita perlu menyimpan seluruh catatan. '
    'HDFS membagi file menjadi potongan yang disebut <strong>blok</strong>, lalu menyimpan '
    'salinannya di beberapa tempat.</p>'+
    '<p><strong>Tujuan demo:</strong> menunjukkan bahwa file tetap dapat dibaca ketika satu tempat penyimpanan gagal.</p>'+
    table(['Nama teknis','Bayangkan sebagai','Tugasnya'],[
        ('NameNode','Daftar lokasi penyimpanan','Mencatat blok mana berada di tempat mana'),
        ('DataNode (DN1, DN2, DN3)','Tiga tempat penyimpanan','Menyimpan potongan file'),
        ('Replika','Salinan blok','Menyediakan salinan yang dapat dibaca ketika tempat lain gagal')])+
    '<p>Misalnya, satu blok disimpan di DN1 dan DN2. Saat DN1 gagal, kita membaca salinan di DN2. '
    'Kemudian salinan pengganti dibuat di DN3 agar blok kembali memiliki dua salinan.</p>'+
    flow(['File dibagi menjadi blok','Tiap blok dibuat 2 salinan','DN1 dibuat gagal','Baca salinan dan pulihkan'])+
    action('storage','Jalankan tahap penyimpanan untuk mencoba pembagian blok dan kegagalan DN1.',
           'jumlah blok, pesan DN1 OFFLINE, dan apakah isi file tetap sama setelah dibaca kembali.')+
    '<h3>Apa hasilnya?</h3>'+table(['Hasil demo','Artinya'],[
        (f'{n(blocks)} blok',f'Empat file input dipecah menjadi total {n(blocks)} potongan'),
        ('2 replika per blok','Setiap potongan memiliki dua salinan'),
        ('DN1 OFFLINE','Satu tempat penyimpanan sengaja dinonaktifkan dalam skenario latihan'),
        ('Isi file tetap cocok','File dibaca dari DN2/DN3 dan pemeriksaan isi berhasil'),
        (f'{len(storage["repairs"])} blok dipulihkan','Blok yang kehilangan satu salinan mendapat salinan pengganti')])+
    '<p>Pemeriksaan <strong>hash</strong> adalah pemeriksaan sidik jari isi file. Hash yang sama membantu memastikan '
    'isi file tidak berubah saat dipotong, disalin, dan digabung kembali.</p>'+
    say('HDFS menyimpan file dalam beberapa potongan dan membuat salinan. '
        'Ketika satu tempat penyimpanan gagal, salinan di tempat lain masih dapat dibaca.')+
    '<details><summary>Lihat contoh isi data yang disimpan</summary>'+
    '<p>Profil berisi satu baris per anak. Riwayat berisi satu baris per pemberian dosis.</p>'+
    table(['ID anak','Provinsi','Kabupaten','Tahun lahir','D1 / D2 / D3'],[
        (r['child_id'],r['province'],r['district'],r['birth_year'],f"{r['dose1']} / {r['dose2']} / {r['dose3']}")
        for r in [children[i] for i in (0,25,29,400)]])+
    table(['ID anak','Dosis','Tanggal','Fasilitas'],[
        (r['child_id'],'DTP'+str(r['dose_number']),r['vaccination_date'],r['facility_id']) for r in events[:3]])+'</details>'+
    '<details><summary>Detail teknis: lokasi blok dan kode</summary>'
    '<p>Ukuran blok latihan 16 KiB agar sampel kecil menghasilkan beberapa blok. '
    'Client mengambil lokasi dari NameNode lalu membaca data langsung dari DataNode. '
    'Hash SHA-256 dicatat di manifest latihan untuk menelusuri integritas; '
    'pada HDFS pemeriksaan checksum melibatkan client/DataNode.</p>'+
    table(['Blok children.tsv','Lokasi awal','Dibaca saat DN1 gagal','Lokasi setelah re-replikasi'],[
        (block['id'],', '.join(block['replicas']),storage['read_after_failure']['children.tsv'][i]['node'],
         ', '.join(storage['after_failure']['files']['children.tsv']['blocks'][i]['replicas']))
        for i,block in enumerate(storage['initial']['files']['children.tsv']['blocks'][:6])])+
    '<p>Tabel menampilkan enam blok pertama; catatan hasil menyimpan seluruh blok.</p>'+
    '<p>Blok adalah potongan byte, sehingga satu baris teks bisa melintasi dua blok. '
    'Penggabungan kembali mempertahankan file utuh. Jejak hasil ada pada <code>hdfs/results.json</code> dalam folder sesi.</p>'+
    source_block('Kode pembagian blok dan pemulihan',read('code/concept_storage.py'))+
    '<p>Contoh perintah HDFS untuk menyimpan file dan melihat daftarnya:</p>'+
    code('hdfs dfs -put data/dummy/children.tsv "$HDFS_BASE/children/children.tsv"\n'
         'hdfs dfs -ls -R "$HDFS_BASE"')+'</details>'+
    next_step('data sudah disimpan. Kita akan membagi pekerjaan untuk menghitung jumlah anak per kabupaten.')))

pages.append(section('case-mapreduce','02 · MAPREDUCE + YARN','Bagi pekerjaan, lalu gabungkan hitungannya',
    badge+f'<p class="lead">Data dari tahap sebelumnya berisi {n(len(children))} anak. '
    'Sekarang kita menghitung anak yang masuk kelompok analisis, penerima D1, dan penerima D3 '
    'untuk setiap kabupaten.</p>'+
    '<p><strong>MapReduce</strong> membagi dan merangkum pekerjaan. '
    '<strong>YARN</strong> mengatur kapasitas CPU/RAM agar pekerjaan mendapat tempat untuk berjalan.</p>'+
    table(['Tahap MapReduce','Apa yang dilakukan pada data kita'],[
        ('Map — baca dan catat',f'Mapper A/B membaca {n(mr["mapper_input_rows"][0])}/{n(mr["mapper_input_rows"][1])} profil '
         f'dan memilih {n(mr["mapper_output_rows"][0])}/{n(mr["mapper_output_rows"][1])} anak yang memenuhi syarat'),
        ('Shuffle/sort — kelompokkan','Catatan dari kedua mapper dikumpulkan berdasarkan provinsi dan kabupaten yang sama'),
        ('Reduce — jumlahkan',f'Jumlah anak, penerima D1, dan penerima D3 dihitung untuk {len(coverage)} kabupaten')])+
    flow([f'{n(len(children))} profil dibagi dua',f'{n(len(cohort))} anak memenuhi syarat','Kelompokkan per kabupaten',f'{len(coverage)} hasil hitungan'])+
    '<h3>Lalu YARN melakukan apa?</h3>'
    '<p>Bayangkan ada beberapa komputer yang bisa mengerjakan tugas. YARN memeriksa kapasitasnya '
    'dan memberi jatah CPU/RAM untuk tiap tugas. Jatah tersebut disebut <strong>container</strong>.</p>'+
    table(['Nama dalam YARN','Arti sederhana'],[
        ('ResourceManager','Pengatur kapasitas seluruh komputer: memilih di mana tugas mendapat jatah CPU/RAM'),
        ('ApplicationMaster','Koordinator satu pekerjaan: meminta jatah dan memantau tugasnya'),
        ('NodeManager (NM1, NM2, NM3)','Pengelola pada tiap komputer: menjalankan tugas sesuai jatah yang diberikan')])+
    '<p>Pada contoh ini, NM1 menampung koordinator. NM2 menjalankan Mapper A dan NM3 menjalankan Mapper B. '
    'Setelah hasil kedua mapper terkumpul, reducer menghitung totalnya. Jatah dilepas setelah tugas selesai.</p>'+
    flow(['Pekerjaan dikirim','Kapasitas disediakan','Tugas berjalan','Selesai, kapasitas dilepas'])+
    action('mapreduce','Setelah storage selesai, jalankan tahap ini untuk melihat pembagian pekerjaan dan hitungannya.',
           f'Mapper A/B mendapat tempat, lalu muncul tabel {len(coverage)} kabupaten. Urutan selesainya mapper boleh berbeda.')+
    '<h3>Contoh membaca hasil: Kabupaten Bandung</h3>'+table(['Angka hasil','Artinya'],[
        (f'{n(utara["eligible_children"])} anak','Jumlah anak Kabupaten Bandung yang memenuhi syarat dalam kelompok analisis'),
        (f'{n(utara["dose1_children"])} penerima D1','Anak dalam kelompok tadi yang sudah menerima dosis pertama'),
        (f'{n(utara["dose3_children"])} penerima D3','Anak dalam kelompok tadi yang sudah menerima dosis ketiga')])+
    '<p>Tahap ini menampilkan jumlah anak dan penerima dosis. '
    'Pada tahap Hive, kita menggunakan SQL untuk melihat persentase cakupan, putus lanjut, dan kabupaten prioritas.</p>'+
    say('MapReduce membagi data ke dua pembaca, mengelompokkan catatan dari wilayah yang sama, '
        'lalu menjumlahkannya. YARN menyediakan kapasitas agar tugas-tugas itu bisa berjalan.')+
    '<details><summary>Coba tambahan: apa yang terjadi saat kapasitas terbatas?</summary>'
    '<p>Perintah berikut mengubah contoh menjadi dua NodeManager. Satu digunakan koordinator, '
    'sehingga tinggal satu tempat untuk mapper. Mapper B harus menunggu Mapper A selesai. '
    'Angka hasil tetap sama.</p>'+
    action('mapreduce --yarn-nodes 2','Jalankan ini bila ingin memperlihatkan antrean.',
           'pesan WAITING berarti menunggu jatah kosong. Opsi --yarn-nodes 2 memilih dua NodeManager.')+'</details>'+
    '<details><summary>Detail teknis: status, jatah CPU/RAM, dan kode</summary>'+
    table(['Status di catatan proses','Artinya'],[
        ('SUBMITTED','Pekerjaan sudah dikirim'),('ACCEPTED','Pekerjaan diterima'),
        ('RUNNING','Pekerjaan sedang berjalan'),('WAITING','Tugas menunggu kapasitas'),
        ('FINISHED / SUCCEEDED','Pekerjaan selesai dengan berhasil')])+
    '<p>Anggaran latihan per NodeManager: 1 CPU/1.024 MiB. ApplicationMaster memakai 1 CPU/256 MiB; '
    'mapper/reducer memakai 1 CPU/512 MiB. Ini jatah dalam model latihan, bukan pengukuran RAM laptop. '
    'Satu MiB adalah satuan ukuran memori.</p>'+
    table(['Container','Tugas','NodeManager','CPU','RAM MiB'],[
        (key,value['task'],value['node'],value['cpu'],value['memory_mb']) for key,value in mr['yarn']['containers'].items()])+
    '<p>Key adalah penanda kelompok, misalnya <code>Jawa Barat|Kabupaten Bandung</code>. '
    'Value adalah angka yang dikirim mapper: satu anak, status D1, dan status D3. '
    'Input split adalah bagian data yang dibaca mapper; berbeda dari blok penyimpanan HDFS. '
    'Pada contoh ini mapper menerima baris profil utuh.</p>'+
    source_block('Urutan lengkap proses yang dijalankan','\n'.join(
        f'{e["sequence"]:02d}. {e["actor"]} {e["event"]} | {e["detail"]}' for e in mr['yarn']['events']))+
    source_block('Kode mapper: baca profil dan keluarkan angka',read('code/registry_mapper.py'))+
    source_block('Kode reducer: jumlahkan per wilayah',read('code/registry_reducer.py'))+
    source_block('Kode alokasi kapasitas YARN',read('code/concept_yarn.py'))+
    source_block('Contoh kode pengiriman pekerjaan Hadoop',read('native/registry/mapreduce.sh'))+
    source_block('Word Count: contoh cadangan menghitung kata',read('output/wordcount.tsv'))+'</details>'+
    next_step('kita membaca ringkasan tiap kabupaten menggunakan SQL dan menafsirkan persentasenya.')))

pages.append(section('analytics','03 · HIVE','Kabupaten mana yang perlu diperhatikan?',
    badge+'<p class="lead">Kita sudah mendapat jumlah anak per kabupaten. '
    'Sekarang kita menjawab pertanyaan yang sama dengan <strong>SQL</strong>, '
    'yaitu bahasa untuk meminta data dari tabel. Hive menyediakan cara analisis ini dalam ekosistem Hadoop.</p>'+
    '<p>Permintaan kita: pilih anak kelahiran 2023 yang memenuhi syarat, kelompokkan menurut kabupaten, '
    'lalu hitung jumlah penerima D1/D3 dan persentasenya. '
    'SQL mengolah data profil yang sama; hasilnya dibandingkan dengan penghitungan MapReduce.</p>'+
    table(['Ukuran','Pertanyaan yang dijawab','Contoh Kabupaten Bandung'],[
        ('Cakupan D3','Dari semua anak yang memenuhi syarat, berapa yang sudah menerima D3?',
         f'{utara["dose3_children"]} / {utara["eligible_children"]} × 100 = {pct(utara["coverage_pct"])}'),
        ('Dropout / putus lanjut D1→D3','Dari anak yang sudah D1, berapa yang belum sampai D3?',
         f'({utara["dose1_children"]} − {utara["dose3_children"]}) / {utara["dose1_children"]} × 100 = {pct(utara["dropout_pct"])}')])+
    action('hive','Jalankan analisis SQL untuk melihat cakupan dan putus lanjut dosis per kabupaten.',
           'tabel persentase dan jumlah kabupaten prioritas. Pemeriksaan kecocokan dengan MapReduce tetap dijalankan; pesannya tampil melalui --detail.')+
    '<h3>Hasil yang perlu dibaca</h3>'+table(['Kabupaten','Anak yang dihitung','Sudah D1','Sudah D3','Cakupan D3','Putus lanjut'],[
        (r['district'],r['eligible_children'],r['dose1_children'],r['dose3_children'],pct(r['coverage_pct']),pct(r['dropout_pct']))
        for r in coverage])+
    '<p><strong>Kabupaten Bandung:</strong> separuh anak sudah D3, tetapi banyak penerima D1 belum sampai D3. '
    '<strong>Kabupaten Semarang:</strong> belum ada penerima D1, sehingga dropout tidak dapat dihitung. '
    '<strong>N/A</strong> berarti tidak ada pembagi untuk perhitungan ini; bukan berarti dropout 0%.</p>'+
    '<p>Untuk contoh tindak lanjut, kita memilih kabupaten dengan cakupan D3 di bawah 80%: '
    '<strong>'+', '.join(html.escape(row['district']) for row in priority)+'</strong>. Batas 80% dipilih untuk latihan.</p>'+
    say('Cakupan melihat semua anak yang memenuhi syarat. Dropout melihat anak yang sudah memulai dosis pertama '
        'tetapi belum sampai dosis ketiga. Keduanya membantu kita memahami masalah yang berbeda.')+
    '<h3>Eksplorasi: berapa putus lanjut keseluruhan?</h3>'+
    '<p>Keseluruhan berarti 12 provinsi dan 24 kabupaten dalam dataset sintetis, bukan statistik seluruh Indonesia. '
    'Jumlahkan penerima D1 dan D3 dahulu, lalu hitung persentasenya. Jangan merata-ratakan persentase kabupaten.</p>'+
    action('hive --analysis overall','Tampilkan ringkasan seluruh wilayah dalam dataset.',
           f'putus lanjut {pct(analysis["overall"]["dropout_pct"])} dan cakupan D3 {pct(analysis["overall"]["coverage_pct"])}.')+
    table(['Ukuran keseluruhan','Jumlah','Persentase'],[
        ('Cakupan D3',f'{n(analysis["overall"]["dose3_children"])} / {n(analysis["overall"]["eligible_children"])}',pct(analysis['overall']['coverage_pct'])),
        ('Putus lanjut D1 ke D3',f'{n(analysis["overall"]["dropout_children"])} / {n(analysis["overall"]["dose1_children"])}',pct(analysis['overall']['dropout_pct']))])+
    '<h3>Eksplorasi: kabupaten mana yang putus lanjutnya tertinggi?</h3>'+
    action('hive --analysis highest','Pilih lima kabupaten dengan putus lanjut tertinggi.',
           'urutan persentase terbesar; kabupaten tanpa penerima D1 tidak masuk ranking.')+
    table(['Urutan','Provinsi / Kabupaten','D1','D3','Putus lanjut'],[
        (i,r['province']+' / '+r['district'],r['dose1_children'],r['dose3_children'],pct(r['dropout_pct']))
        for i,r in enumerate(analysis['highest'],1)])+
    '<h3>Eksplorasi: kabupaten mana yang putus lanjutnya terendah?</h3>'+
    action('hive --analysis lowest','Pilih lima kabupaten dengan putus lanjut terendah.',
           'urutan persentase terkecil yang bisa dihitung. N/A bukan nol.')+
    table(['Urutan','Provinsi / Kabupaten','D1','D3','Putus lanjut'],[
        (i,r['province']+' / '+r['district'],r['dose1_children'],r['dose3_children'],pct(r['dropout_pct']))
        for i,r in enumerate(analysis['lowest'],1)])+
    '<p>Nilai sama diurutkan berdasarkan nama provinsi/kabupaten; lima baris bukan berarti lima tingkat persentase yang berbeda. '
    'Dropout rendah perlu dibaca bersama cakupan: anak yang belum D1 tidak menjadi pembagi dropout.</p>'+
    '<details><summary>Bandingkan provinsi atau ubah jumlah hasil</summary>'+
    command('hive --analysis province')+
    table(['Provinsi','Anak dihitung','D1','D3','Cakupan D3','Putus lanjut'],[
        (r['province'],r['eligible_children'],r['dose1_children'],r['dose3_children'],pct(r['coverage_pct']),pct(r['dropout_pct']))
        for r in analysis['province']])+
    '<p>Untuk sepuluh hasil tertinggi, tambahkan --limit 10. Untuk seluruh analisis, pilih --analysis all.</p>'+
    command('hive --analysis highest --limit 10')+command('hive --analysis all')+'</details>'+
    '<details><summary>Detail teknis: query SQL dan tabel Hive</summary>'
    '<p>SELECT memilih hasil; WHERE membatasi anak yang dihitung; GROUP BY mengelompokkan wilayah; '
    'SUM menjumlahkan status dosis. NULLIF menjaga agar query tidak membagi angka dengan nol.</p>'+
    source_block('Query yang menghitung cakupan dan dropout',read('native/registry/coverage.sql'))+
    source_block('Query putus lanjut keseluruhan',read('native/registry/analysis_overall.sql'))+
    source_block('Query top 5 tertinggi',read('native/registry/analysis_highest.sql'))+
    source_block('Query top 5 terendah',read('native/registry/analysis_lowest.sql'))+
    '<p>External table memberi nama dan susunan kolom pada file input. LOCATION menunjukkan lokasi filenya. '
    'Hive dapat memakai mesin pemrosesan yang berbeda sesuai konfigurasi.</p>'+
    source_block('Contoh definisi external table',read('native/registry/setup_hive.hql'))+'</details>'+
    next_step('setelah melihat kabupatennya, kita membuat daftar anak yang belum menerima D3.')))

pages.append(section('etl','04 · PIG','Pilih anak yang belum menerima dosis ketiga',
    badge+'<p class="lead">Ringkasan kabupaten belum memberi daftar nama atau ID anak. '
    'Pig membantu menulis urutan penyaringan data agar kita mendapatkan daftar anak yang perlu ditelusuri.</p>'+
    '<p>Proses membaca, memilih, lalu menyimpan data ini disebut <strong>ETL</strong>. '
    'Kita memilih kelompok kelahiran 2023 yang memenuhi syarat, lalu memilih yang belum D3.</p>'+
    flow([f'Baca {n(len(children))} profil',f'Pilih {n(len(cohort))} yang memenuhi syarat',f'Pilih {n(len(missed))} yang belum D3','Pisahkan daftar tindak lanjut'])+
    action('pig','Jalankan penyaringan untuk membuat daftar kelompok analisis dan daftar yang belum D3.',
           f'urutan {n(len(children))} → {n(len(cohort))} → {n(len(missed))} dan contoh ID anak yang terpilih.')+
    '<h3>Empat file untuk tujuan berbeda</h3>'+table(['File hasil','Isi','Kegunaan'],[
        ('cohort.csv',f'{n(len(cohort))} anak yang memenuhi syarat','Kelompok lengkap untuk analisis'),
        ('missed_dose3.csv',f'{n(len(missed))} anak dari kelompok tadi yang belum D3','Daftar lengkap yang belum D3'),
        ('dropout_d1_d3.csv',f'{n(len(dropout))} anak sudah D1 tetapi belum D3','Daftar putus lanjut'),
        ('not_started_d1.csv',f'{n(len(not_started))} anak belum memulai D1','Daftar yang belum memulai imunisasi')])+
    f'<p><strong>{n(len(missed))} belum D3 = {n(len(dropout))} putus lanjut + {n(len(not_started))} belum memulai D1.</strong></p>'+
    '<h3>Telusuri wilayah hasil analisis Hive</h3>'+
    '<p>Kabupaten Jember termasuk wilayah dengan putus lanjut tertinggi dalam dataset. '
    'Pilih provinsi dan kabupatennya untuk membuat daftar anak di wilayah tersebut.</p>'+
    command('pig --province "Jawa Timur" --district "Kabupaten Jember"')+
    '<p>Buka dropout_d1_d3.csv pada folder hasil, lalu ambil ID anak untuk pencarian HBase. '
    'Pemilihan kabupaten memakai nama provinsi juga agar wilayahnya tidak tertukar.</p>'+
    '<p>Contoh ID yang dapat ditelusuri: <strong>D000030</strong>. Anak ini sudah D1 dan D2, tetapi belum D3. '
    'Daftar belum D3 juga dapat memuat anak yang belum menerima D1 sama sekali. '
    'Itulah sebabnya jumlah belum D3 berbeda dari jumlah putus lanjut setelah D1.</p>'+
    say(f'Pig menyaring data langkah demi langkah. Dari {n(len(children))} anak kita memilih {n(len(cohort))} yang memenuhi syarat, '
        f'lalu menemukan {n(len(missed))} yang belum dosis ketiga. Hasilnya berupa daftar anak, bukan hanya persentase kabupaten.')+
    '<details><summary>Lihat contoh anak dan kode penyaringan</summary>'+
    table(['ID anak','Kabupaten','Sudah D1','Sudah D2','Sudah D3'],[
        (r['child_id'],r['district'],r['dose1'],r['dose2'],r['dose3']) for r in missed[:5]])+
    '<p>Dalam Pig Latin: LOAD berarti baca file, FILTER berarti pilih baris sesuai kondisi, '
    'dan STORE berarti simpan hasil. Data tahun lahir lain tetap ada di sumber, tetapi tidak masuk daftar yang dipilih.</p>'+
    source_block('Kode Pig Latin: baca → pilih → simpan',read('native/registry/etl.pig'))+'</details>'+
    next_step('ambil satu ID dari daftar tadi dan lihat riwayatnya melalui HBase.')))

pages.append(section('lookup','05 · HBASE','Cari riwayat satu anak dari ID-nya',
    badge+f'<p class="lead">Dari daftar {n(len(missed))} anak belum D3, kita memilih ID <strong>D000030</strong>. '
    'HBase digunakan untuk mencari catatan berdasarkan kunci tertentu, seperti ID anak.</p>'+
    '<p>ID anak disebut <strong>row key</strong>: penanda untuk menemukan satu baris. '
    'Informasinya dikelompokkan menjadi <strong>profile</strong> untuk identitas dan '
    '<strong>history</strong> untuk riwayat dosis. Kelompok kolom ini disebut <strong>column family</strong>.</p>'+
    flow(['Pilih ID dari daftar Pig','Cari ID D000030','Baca profil dan riwayat','DTP3 belum diterima'])+
    action('hbase --child D000030','Jalankan pencarian untuk anak yang dipilih. Opsi --child menentukan ID yang dicari.',
           'anak ditemukan di Kabupaten Bandung, memiliki catatan DTP1/DTP2, dan belum menerima DTP3.')+
    '<div class="split"><div class="card"><h3>Anak yang ditemukan</h3>'+table(['Informasi','Hasil'],[
        ('ID anak',history['child_id']),('Provinsi',history['profile']['province']),
        ('Kabupaten',history['profile']['district']),('Tanggal lahir',history['profile']['birth_date'])])+ '</div>'+
    '<div class="card"><h3>Riwayat pemberian dosis</h3>'+table(['Dosis','Tanggal','Fasilitas'],[
        ('DTP'+str(r['dose_number']),r['vaccination_date'],r['facility_id']) for r in history['history']])+
    '<p><strong>DTP3 belum diterima.</strong> Kita dapat melihat dosis yang sudah ada tanpa menghitung ulang seluruh kabupaten.</p></div></div>'+
    say('Setelah mendapatkan daftar anak yang belum dosis ketiga, kita memilih satu ID. '
        'HBase mencari ID itu dan menampilkan profil serta riwayat dosisnya.')+
    '<details><summary>Pahami bentuk kolom HBase dan contoh kodenya</summary>'+
    table(['Istilah','Arti','Contoh'],[
        ('Row key','ID baris yang dicari','D000030'),('Column family','Kelompok kolom','history'),
        ('Qualifier','Nama kolom dalam kelompok','DTP1'),('Value','Isi kolom','2023-06-01|FAC01')])+
    '<p><code>history:DTP1</code> dibaca “kolom DTP1 dalam kelompok history”. '
    'Isinya adalah tanggal pemberian dosis dan kode fasilitas.</p>'+
    table(['Row key','Column family','Qualifier','Value'],[
        (cell['row_key'],cell['family'],cell['qualifier'],cell['value']) for cell in cells
        if cell['family']=='history' or cell['qualifier'] in ('province','district')])+
    '<p>HBase disebut wide-column karena data diatur menurut row key dan kelompok kolom. '
    'Tanggal vaksinasi di value berbeda dari timestamp versi sel. Kode PUT menyimpan catatan; GET mengambilnya.</p>'+
    source_block('Contoh PUT dan GET untuk satu anak',read('native/registry/lookup.hbase'))+'</details>'+
    '<details><summary>Coba ID lain: catatan kosong atau anak tidak ditemukan</summary>'
    f'<p>{empty_child} adalah anak yang terdaftar tetapi belum mempunyai catatan dosis. '
    'TIDAK_ADA adalah ID yang tidak ada dalam data. Keduanya harus dibedakan.</p>'+
    '<p>Untuk melihat anak yang terdaftar dengan riwayat kosong, ketik:</p>'+command('hbase --child '+empty_child)+
    '<p>Untuk melihat hasil ID yang tidak ditemukan, ketik:</p>'+command('hbase --child TIDAK_ADA')+'</details>'+
    next_step('rangkum peran alat dan manfaat hasil yang sudah kita lihat.')))

pages.append(section('real','PELENGKAP · WHO/UNICEF','Data WHO menjawab pertanyaan yang berbeda',
    '<p class="lead">Data WHO/UNICEF yang disimpan di proyek adalah ringkasan menurut negara dan tahun. '
    'Data ini cocok untuk melihat tren nasional. Data buatan pada demo utama memberi catatan per anak '
    'agar penyaringan dan pencarian riwayat dapat diperlihatkan.</p>'+
    table(['Contoh pertanyaan','Data yang sesuai'],[
        ('Berapa perkiraan cakupan DTP3 Indonesia pada tahun tertentu?','Data WHO/UNICEF: ringkasan negara/tahun'),
        ('Anak mana di Kabupaten Bandung yang belum D3, dan kapan menerima D1?','Data demo: profil dan catatan dosis per anak')])+
    '<p>Data WHO tidak memuat ID anak atau provinsi untuk melakukan pencarian tersebut. '
    'Data buatan dibuat terpisah dan tidak diturunkan dari persentase WHO.</p>'+
    '<details><summary>Lihat pelengkap WHO jika ingin membahas tren antarnegara</summary>'
    '<p>Pelengkap ini memakai lima negara pada tahun 2020–2025. '
    'Angkanya adalah ringkasan nasional, sehingga cara membacanya berbeda dari riwayat seorang anak.</p>'
    '<p><a href="../who-presentation/index.html">Buka hasil WHO lima negara</a> · '
    '<a href="../../DEMO_MANUAL_WHO_WINDOWS.md">Baca panduan pelengkap WHO</a></p></details>'))

pages.append(section('close','PENUTUP','Apa yang sudah kita pelajari?',
    '<p class="lead">Kita mengikuti catatan imunisasi dari penyimpanan sampai daftar anak dan riwayat dosisnya. '
    'Setiap alat membantu menjawab satu bagian dari pertanyaan awal.</p>'+
    table(['Alat','Ingat tugas utamanya'],[
        ('HDFS','Simpan potongan file dan salinannya agar data tetap dapat dibaca'),
        ('YARN','Atur jatah CPU/RAM untuk menjalankan pekerjaan'),
        ('MapReduce','Bagi data, kelompokkan, lalu jumlahkan hasilnya'),
        ('Hive','Gunakan SQL untuk meringkas dan menganalisis data'),
        ('Pig','Pilih data langkah demi langkah dan simpan daftar hasilnya'),
        ('HBase','Cari profil dan riwayat berdasarkan satu ID anak')])+
    say(f'Dari {n(len(children))} anak, kita memilih {n(len(cohort))} yang memenuhi syarat. '
        f'Sebanyak {n(sum(row["dose3"] for row in cohort))} sudah menerima dosis ketiga dan {n(len(missed))} belum. '
        'Ringkasan kabupaten membantu memilih wilayah yang perlu diperhatikan, '
        'sedangkan daftar ID membantu menelusuri riwayat tiap anak.')+
    '<h3>Hubungannya dengan 5V Big Data</h3>'
    '<p>5V membantu menjelaskan tantangan dan manfaat data. Sampel kecil ini digunakan untuk mengikuti alur; '
    'skala besar dan pembaruan yang terus masuk menjadi konteks pengembangannya.</p>'+
    table(['5V','Arti sederhana','Pada contoh imunisasi'],[
        ('Volume','Banyaknya data',f'Registri nasional dapat berisi banyak anak; latihan ini memakai {n(len(children))}'),
        ('Velocity','Seberapa cepat data masuk/diperbarui','Catatan baru dapat datang setiap hari; latihan ini memakai satu kumpulan data'),
        ('Variety','Beragam bentuk dan sumber data','Profil anak dan catatan dosis memiliki kolom berbeda; ganti format file saja tidak menambah keragaman sumber'),
        ('Veracity','Seberapa dapat dipercaya datanya','Periksa ID unik, urutan tanggal/dosis, dan kecocokan profil dengan riwayat'),
        ('Value','Manfaat yang diperoleh','Temukan wilayah bercakupan rendah dan anak yang belum menerima D3')])+
    '<p>Hasil ini membantu menjelaskan tindak lanjut imunisasi. Prediksi wabah merupakan pekerjaan lanjutan '
    'yang memerlukan data tambahan, model, dan pengujian.</p>'+
    '<h3>Ingin mengulang latihan?</h3><p>Untuk melihat seluruh tahap sekaligus, jalankan perintah di bawah. '
    '<code>all</code> berarti semua tahap. Program membuat sesi baru dan menyimpan hasil setiap percobaan '
    'dalam folder baru. Saat presentasi, jalankan perintah per tahap agar mudah dijelaskan.</p>'+command('all')+
    '<p>Nama folder hasil muncul di akhir proses. Memulai lagi dengan <code>storage</code> membuat sesi baru. '
    'Mengulang tahap lain menggunakan sesi yang sedang aktif tanpa menimpa hasil sebelumnya.</p>'+
    '<p><a href="../../DEMO_MANUAL_WINDOWS.md">Panduan langkah demi langkah</a> · '
    '<a href="../../PANDUAN_DEMO_HASIL.md">Kalimat untuk menjelaskan tiap tahap</a></p>'+
    '<details><summary>File hasil dan catatan teknis</summary><ul>'
    '<li><a href="../../data/dummy/README.md">Kolom dan asumsi data buatan</a></li>'
    f'<li><a href="registry_coverage.csv">Cakupan dan putus lanjut {len(coverage)} kabupaten</a></li>'
    f'<li><a href="registry_missed_dose3.csv">Daftar {n(len(missed))} anak belum dosis ketiga</a></li>'
    '<li><a href="registry_lookup.json">Hasil pencarian D000030</a></li>'
    '<li><a href="registry_column_cells.csv">Contoh kolom HBase</a></li>'
    '<li><a href="registry_analysis.json">Ringkasan keseluruhan, ranking putus lanjut, dan perbandingan provinsi</a></li>'
    '<li><a href="registry_dropout_d1_d3.csv">Daftar anak sudah D1 tetapi belum D3</a></li>'
    '<li><a href="registry_not_started_d1.csv">Daftar anak belum memulai D1</a></li>'
    '<li><a href="registry-storage/hdfs/results.json">Catatan pembacaan dan pemulihan blok</a></li>'
    '<li><a href="registry-mapreduce/yarn.json">Catatan jatah kapasitas dan urutan pekerjaan</a></li>'
    '<li><a href="evidence.json">Catatan perhitungan dan pemeriksaan sumber</a></li></ul></details>'))

style = '''
:root{--ink:#152c45;--muted:#51647a;--line:#d8e2ec;--blue:#1166a8;--bg:#f3f7fa}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.6 "Segoe UI",Arial,sans-serif}header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);z-index:5;padding:12px 4vw;display:flex;justify-content:space-between;align-items:center;gap:16px}header strong{font-size:18px}nav{display:flex;gap:6px;flex-wrap:wrap}nav a{font-size:14px;color:var(--muted);text-decoration:none;padding:6px 10px;border-radius:6px}nav a:hover,nav a.active{background:#e4f0fa;color:var(--blue)}main{max-width:1320px;margin:auto;padding:0 4vw}section{padding:42px 0 50px;scroll-margin-top:80px;border-bottom:1px solid var(--line)}h1{font-size:clamp(34px,4vw,54px);line-height:1.15;margin:15px 0}h2{font-size:clamp(28px,3vw,40px);line-height:1.25;margin:10px 0 16px}h3{font-size:20px;margin:0 0 12px}.eyebrow{color:var(--blue);font-weight:700;font-size:13px;letter-spacing:1.7px}.lead{font-size:21px;max-width:1000px;color:var(--muted)}.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700}.local{background:#ddf2e8;color:#176441}.design{background:#fff0d9;color:#825510}.split{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:22px 0}.card{padding:22px;border:1px solid var(--line);border-radius:12px;background:#fff;min-width:0}.card p{font-size:16px}.card .split{gap:12px;margin:8px 0}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:28px 0}.metrics div{background:#fff;border-left:4px solid var(--blue);padding:20px;border-radius:4px}.metrics strong{display:block;font-size:36px;line-height:1.3}.metrics span{color:var(--muted);font-size:15px}.flow{display:flex;gap:10px;align-items:stretch;margin:24px 0}.flow div{flex:1;background:#e7f0f8;padding:14px;border-radius:6px;position:relative;font-size:16px;font-weight:600}.flow div+div::before{content:"→";position:absolute;left:-14px;top:14px;color:var(--blue);font-size:19px}.note{background:#fff8e9;border-left:4px solid #d2a344;padding:14px 18px;font-size:16px}.source{font-size:14px;color:var(--muted)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff;font-size:17px}th,td{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line)}th{background:#e7f0f8;font-size:14px}pre{background:#13293d;color:#e5f0fa;padding:16px;border-radius:8px;overflow:auto;font:14px/1.6 Consolas,monospace;tab-size:4}details{margin:12px 0;border:1px solid var(--line);border-radius:8px;padding:10px 14px;background:#fff}summary{cursor:pointer;color:var(--blue);font-size:15px;font-weight:600}a{color:var(--blue)}blockquote{font-size:22px;border-left:4px solid var(--blue);margin:25px 0;padding:10px 22px;background:#e7f0f8}.sources{font-size:15px}.sources li{margin:5px 0}footer{font-size:13px;color:var(--muted);padding:22px 4vw}ol{padding-left:22px;font-size:17px}button{border:1px solid var(--line);background:white;border-radius:6px;padding:7px 10px;color:var(--blue);cursor:pointer}.action{margin:26px 0;padding:20px 22px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:8px}.action p{margin:10px 0;font-size:17px}.action pre{margin:14px 0}.next-step{padding:14px 18px;background:#e7f0f8;border-radius:6px;font-size:17px}blockquote{font-size:19px}section>p{max-width:1050px}@media(max-width:760px){header{position:static;display:block}.split,.metrics{grid-template-columns:1fr}.flow{flex-wrap:wrap}.flow div{min-width:40%}.flow div+div::before{content:""}section{padding:30px 0}}@media print{header,details{display:none}section{break-before:page;border:0;padding:15px 0}.card,table,.note{break-inside:avoid}body{font-size:14px}main{padding:0}.lead{font-size:17px}pre{white-space:pre-wrap}.metrics strong{font-size:26px}}
'''


nav = ''.join(f'<a href="#{id_}">{label}</a>' for id_,label in [
    ('intro','Mulai'),('storage','1. Simpan'),('case-mapreduce','2. Hitung'),
    ('analytics','3. Analisis'),('etl','4. Pilih'),('lookup','5. Cari'),('real','WHO'),('close','Ringkasan')])
page = ('<!doctype html><html lang="id"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Modul 4 — Demo Registri Imunisasi Dummy</title><style>'+style+'</style></head><body>'
    '<header><strong>Hadoop Ecosystem · Modul 4</strong><nav>'+nav+'</nav></header><main>'+''.join(pages)+'</main>'
    '<footer>Modul 4 · Hadoop Ecosystem · studi kasus registri imunisasi</footer>'
    '<script>const sections=[...document.querySelectorAll("section")];'
    'const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){'
    'document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("active",a.hash==="#"+entry.target.id));}}},'
    '{rootMargin:"-20% 0px -55% 0px"});sections.forEach(s=>observer.observe(s));</script></body></html>')
(OUT/'index.html').write_text(page,encoding='utf-8')
save_json(OUT/'evidence.json',{
    'built_utc':datetime.now(timezone.utc).isoformat(),'synthetic':True,'dataset':metadata,
    'runtime':'Windows Python/SQLite','sql_query':'native/registry/coverage.sql',
    'coverage':coverage,'cohort_rows':len(cohort),'missed_dose3':len(missed),'analysis':analysis,
    'dropout_children':len(dropout),'never_started_dose1':len(not_started),
    'mapreduce':mr,'lookup':history,'priority_districts':priority,
    'storage':storage,'column_cells':cells,
    'priority_rule':'Invented <80% threshold; not outbreak prediction',
    'native_execution':{key:'NOT RUN' for key in ('HDFS','YARN','Hive','Pig','HBase')}})
print('Created:',OUT/'index.html')
print('Verified:',len(children),'children /',len(events),'events;',len(cohort),'eligible;',len(missed),'missed D3;',len(coverage),'SQL/MapReduce results match.')
print('Verified: D000030 dose history; source hashes and profile/event integrity.')
