# Modul 4 — Hadoop Ecosystem

Paket pendamping presentasi berdasarkan **Modul 4.pdf**, halaman PDF 1–5 (nomor cetak 31–35). Materi presentasi, demo lokal yang berjalan tanpa dependency tambahan, dan kode untuk lingkungan Hadoop disediakan terpisah.

Seluruh pengerjaan berada di `C:\Kuliah\Semester 5\Big Data\HadoopEcosystem`. Salinan PDF sumber tersedia di [`source/Modul 4.pdf`](source/Modul%204.pdf); kode, data, panduan, dan hasil demo juga tersimpan di dalam folder proyek ini.

Pembersihan 12 Oktober 2026 memindahkan cadangan revisi, skrip sementara, cache Python, hasil WHO yang tersisa di folder presentasi utama, dan image instalasi Ubuntu ke Recycle Bin. Rincian tersedia di [`output/cleanup-report.json`](output/cleanup-report.json). Dataset utama, halaman presentasi/dashboard, pelengkap WHO yang masih ditautkan, dan disk VM terdaftar dipertahankan. Folder `tmp/` tersedia untuk pengujian berikutnya.

## Demo utama — registri imunisasi dummy

Mulai dari [panduan langkah demi langkah](DEMO_MANUAL_WINDOWS.md). Tiap tahap menjelaskan tujuan, cara kerja sederhana, perintah yang diketik, dan hasil yang perlu diperhatikan. [Narasi presentasi](PANDUAN_DEMO_HASIL.md) menyediakan kalimat untuk menghubungkan satu tahap ke tahap berikutnya. Detail teknis dan kode di halaman presentasi tersedia dalam bagian yang dapat dibuka.

Gunakan **Python/SQLite di Windows** untuk empat tahap manual, ditambah lookup singkat per anak. Panduan: [`DEMO_MANUAL_WINDOWS.md`](DEMO_MANUAL_WINDOWS.md). Halaman [`output/presentation/index.html`](output/presentation/index.html) menampilkan alur, kode, dan hasil pembanding; tidak menjalankan job atau otomatis memuat sesi terminal terbaru.

Dashboard hasil aktual tersedia di [`output/dashboard/index.html`](output/dashboard/index.html). Jalankan `python code/dashboard_server.py`, lalu buka http://127.0.0.1:8765. Dashboard dimulai kosong dan mengikuti sesi `storage` baru; setiap tahap terisi setelah selesai. Panduan: [PANDUAN_DASHBOARD.md](PANDUAN_DASHBOARD.md). Tidak membutuhkan library tambahan.

Data utama: **80.137 anak sintetis**, **12 provinsi**, **24 kabupaten**, **112.931 catatan dosis**. Profil anak dan event dosis konsisten serta memiliki tanggal. Nama wilayah asli Indonesia; data anak, status dosis, eligibility, dan tanggal adalah asumsi pembelajaran. Detail: [`data/dummy/README.md`](data/dummy/README.md).

Perintah berikut dijalankan satu per satu di PowerShell dari folder proyek: storage menyimpan data; mapreduce menghitung jumlah per kabupaten; hive menghitung persentase dari data profil dengan SQL; pig membuat daftar anak belum D3; hbase mencari riwayat satu ID. D1/D3 berarti dosis pertama/ketiga, dan eligible berarti memenuhi syarat untuk dihitung.

```powershell
python code/demo.py storage
python code/demo.py mapreduce
python code/demo.py hive
python code/demo.py pig
python code/demo.py hbase --child D000030
```

Analisis kohort 2023: **20.035 eligible → 10.655 menerima D3 → 9.380 belum D3**. Tampilan MapReduce menunjukkan jumlah anak, penerima D1, dan penerima D3 per kabupaten. Hive menampilkan persentase cakupan/putus lanjut dan kabupaten prioritas. Hasil kedua cara penghitungan tetap dibandingkan sebagai pemeriksaan. ETL memilih kohort dan dosis terlewat. Lookup menampilkan profil dan tanggal DTP1/DTP2 milik D000030; DTP3 belum diterima.

Setiap `storage` membuat sesi baru. Tahap lain dapat diulang pada sesi aktif; setiap eksekusi memiliki folder percobaan baru di `output/manual-demo/runs/`, sehingga hasil sebelumnya tetap tersedia. `python code/demo.py all` menjalankan kelima tahap untuk latihan.

Eksplorasi tujuan analisis: `python code/demo.py hive --analysis highest` atau `lowest` untuk top 5 putus lanjut; `--analysis overall` untuk keseluruhan dataset; `--analysis province` untuk perbandingan provinsi. Tambahkan `--limit 10` untuk sepuluh hasil ranking. SQL mengecualikan D1=0 dan menghitung persentase keseluruhan dari total jumlah anak, bukan rata-rata persentase kabupaten. Keseluruhan sampel menghasilkan **26,37% putus lanjut**; ini bukan estimasi seluruh Indonesia.

Pig juga memisahkan **3.816 anak putus lanjut** dari **5.564 anak belum memulai D1**. Pilih wilayah dengan `python code/demo.py pig --province "Jawa Timur" --district "Kabupaten Jember"`, lalu gunakan ID dari `dropout_d1_d3.csv` untuk pencarian HBase. Langkah lengkap tersedia di [panduan demo](DEMO_MANUAL_WINDOWS.md).

Nama tahap mengikuti komponen modul. Python/SQLite memperagakan blok/replika, metadata dan pemulihan DataNode, alokasi container YARN, map–shuffle–reduce, query SQL, ETL, dan lookup row key/column family. Storage menulis 962 blok dengan faktor replika 2; DN1 dinonaktifkan dan 641 blok mendapat replika pengganti. Mapper/reducer berjalan sebagai subprocess mengikuti alokasi resource. Kode pendamping Hadoop tersedia di [`native/registry/`](native/registry/README.md).

Perintah standar MapReduce memakai tiga NodeManager dalam model anggaran CPU/RAM. Untuk menunjukkan antrean resource, jalankan `python code/demo.py mapreduce --yarn-nodes 2`: satu node menampung ApplicationMaster, dan mapper berjalan bergantian pada slot yang tersedia. Hasil hitungan tetap sama. Contoh column family HBase tampil di terminal dan tersimpan sebagai `column_cells.csv`.

Terminal menampilkan hasil utama secara default: status penyimpanan, tabel penghitungan, analisis terpilih, jumlah hasil ETL, dan riwayat ID. Narasi konsep dan rincian teknis tersedia di panduan atau melalui `--detail` pada setiap tahap, termasuk storage. Lokasi hasil ditulis relatif terhadap root proyek; file hasil lengkap tetap disimpan pada setiap percobaan.

Aturan prioritas cakupan <80% adalah contoh buatan, bukan standar klinis atau prediksi wabah. Dataset kecil tidak membuktikan jutaan rekaman/seluruh 5V; prediksi wabah memerlukan data dan model tambahan.

Pembuatan ulang serta validasi:

```powershell
python code/prepare_dummy_dataset.py
python code/test_registry_demo.py
python code/test_concept_models.py
python code/build_presentation_demo.py
```

## Pelengkap — data nyata WHO/UNICEF

Dataset WHO/UNICEF WUENIC tetap disimpan utuh di [`data/real/`](data/real/README.md): 20.032 observasi, 296 kode wilayah/kelompok, 1980–2025. Subset Indonesia tetap tersedia dengan 90 observasi. Data ini adalah estimasi agregat negara/tahun; tidak memiliki ID anak, provinsi, atau riwayat dosis individual.

Pelengkap lima negara 2020–2025 dipertahankan di [`output/who-presentation/index.html`](output/who-presentation/index.html), dengan panduan [`DEMO_MANUAL_WHO_WINDOWS.md`](DEMO_MANUAL_WHO_WINDOWS.md). Perintahnya menggunakan `code/manual_who_demo.py`; hasil manual WHO disimpan terpisah di `output/manual-who/`.

```powershell
python code/manual_who_demo.py all
python code/build_who_presentation.py
```

WHO dan dummy merupakan dua contoh terpisah. Data dummy tidak merekonstruksi anak dari persentase WHO. Snapshot/provenance/hash sumber WHO tetap berada di `source/real/`. `code/prepare_real_dataset.py` memakai snapshot lokal secara default; tidak perlu mengambil dataset baru.

## Latihan dasar lama — Word Count dan sampel 21 anak

Dari PowerShell di folder proyek:

```powershell
python code/run_demo.py all
python code/test_demo.py
Start-Process .\output\demo_report.html
```

Pilihan untuk mendemokan satu bagian:

```powershell
python code/run_demo.py wordcount
python code/run_demo.py case --child A004
```

Python 3.9+ cukup. Tidak perlu pip, Docker, database server, atau instalasi Hadoop untuk **demo lokal**. Demo memakai Python dan SQLite bawaan Python. Mapper/reducer benar-benar dieksekusi sebagai proses terpisah; shuffle/sort dilakukan lokal. Tidak ada distribusi data, penjadwalan YARN, atau fault tolerance yang dibuktikan oleh demo ini.

## File yang digunakan

| File | Peran |
|---|---|
| `PANDUAN_PRESENTASI.md` | Urutan materi, narasi, cara demo, jawaban pertanyaan |
| `code/demo.py` | Lima tahap manual registri dummy dengan sesi/folder baru |
| `code/concept_storage.py` | Blok byte, metadata, replika, pembacaan dan pemulihan node |
| `code/concept_yarn.py` | Anggaran resource, alokasi container, antrean dan lifecycle aplikasi |
| `code/test_concept_models.py` | Uji kegagalan replika, pembacaan, antrean dan pelepasan resource |
| `code/prepare_dummy_dataset.py` | Generator deterministik dan validasi profil/riwayat |
| `code/indonesia_regions.py` | Katalog pasangan nama provinsi dan kabupaten/kota Indonesia |
| `code/registry_mapper.py`, `code/registry_reducer.py` | Agregasi jumlah anak per kabupaten |
| `data/dummy/` | 80.137 profil, 12 provinsi/24 kabupaten, dan 112.931 catatan dosis |
| `native/registry/` | Padanan kode Hadoop/Hive/Pig/HBase yang belum diuji native |
| `code/mapper.py` | Emit pasangan kata dan angka 1 dari stdin |
| `code/reducer.py` | Jumlahkan key yang sudah dikelompokkan |
| `code/run_demo.py` | Jalankan Word Count, ETL, SQL, dan lookup lokal |
| `data/sample.txt` | Input Word Count |
| `data/students.csv` | Data latihan query GPA dari modul |
| `data/vaccinations.csv` | 21 baris data imunisasi sintetis |
| `native/coverage.sql` | Query agregasi kasus; dipakai di SQLite dan disediakan untuk Hive |
| `native/setup_hive.hql` | Definisi external table Hive dan query students |
| `native/etl_imunisasi.pig` | Pig Latin: load → cohort → missed → store |
| `native/hbase_lookup.hbase` | Contoh insert dan get satu row key |
| `native/run_hadoop.sh` | Unggah HDFS dan jalankan Hadoop Streaming pada YARN |
| `output/demo_report.html` | Tampilan hasil demo dengan kode yang bisa dibuka |

## Hasil latihan dasar lama yang diharapkan

Word Count: `hadoop=3, hive=3, hdfs=1, pig=1, yarn=1`. Query students dengan `gpa > 3.0`: Ani 3.8, Citra 3.5, Eka 3.2.

| Distrik sintetis | Eligible | D1 | D3 | Cakupan D3 | Dropout D1→D3 |
|---|---:|---:|---:|---:|---:|
| Selatan | 6 | 0 | 0 | 0% | N/A |
| Utara | 6 | 5 | 3 | 50% | 40% |
| Tengah | 6 | 4 | 4 | 66.67% | 0% |

ETL memilih 18 anak kohort 2023 yang sudah eligible dosis ketiga dari 21 baris. Sebelas anak belum menerima dosis ketiga. Dua anak kohort 2025 dan satu anak kohort 2022 tidak masuk denominator. `dose3_due` adalah flag eligibility buatan untuk pembelajaran; bukan aturan jadwal imunisasi klinis. Status 0 di data demo berarti belum menerima, bukan status yang tidak diketahui. Dalam data nyata, missing/unknown harus dipisahkan.

## Opsi native untuk latihan dasar lama

Perintah pada bagian ini memakai input latihan dasar lama, bukan registri 80.137 anak. Panduan demo utama ada di [DEMO_MANUAL_WINDOWS.md](DEMO_MANUAL_WINDOWS.md); padanan native untuk dataset utama ada di [native/registry/README.md](native/registry/README.md).

**Penyiapan laptop 8 Oktober 2026:** image Ubuntu sudah diunduh dan diverifikasi, VM `HadoopEcosystem-Modul4` sudah didaftarkan di VirtualBox. Boot dan pemasangan layanan masih menunggu RAM host bebas yang cukup; native HDFS/YARN/Hive/Pig **belum diuji**. Lihat `native/environment/README.md` dan `output/environment/host-status.json` sebelum menjalankan panduan manual.

Gunakan **lingkungan Linux/VM/lab yang sudah disiapkan** dengan HDFS, YARN, Hadoop Streaming, dan Python 3 tersedia di setiap worker. Hive memerlukan metastore dan HiveServer2/Beeline yang sesuai. Java 21 yang terdeteksi di Windows ini bukan bukti kompatibilitas dengan distribusi lab; ikuti versi Java distribusi tersebut. WSL, Docker, Hadoop, dan Hive belum tersedia sebagai lingkungan demo siap pakai di laptop ini saat pemeriksaan.

Jalankan dari root proyek di Linux/VM. Temukan JAR Streaming dalam distribusi Hadoop dan isi path yang benar:

```bash
export HADOOP_STREAMING_JAR=/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-VERSI.jar
bash native/run_hadoop.sh
```

`VERSI` adalah pengganti nama file aktual. Script membuat namespace HDFS baru, tidak menghapus output lama, dan mencetak `HDFS_BASE`. Output mapreduce harus belum ada saat job dimulai. Script tidak memformat NameNode dan tidak memasang layanan.

Salin **nilai aktual** `HDFS_BASE` dari output script. Tentukan URL JDBC HiveServer2 dari lingkungan lab (autentikasi dan konfigurasi mengikuti lab):

```bash
export HDFS_BASE='/user/NAMA_USER/modul4-NILAI_DARI_SCRIPT'
export HIVE_JDBC_URL='jdbc:hive2://HOST_LAB:10000/default'

beeline -u "$HIVE_JDBC_URL" \
  --hivevar hdfs_base="$HDFS_BASE" \
  -i native/setup_hive.hql -f native/coverage.sql

pig -x mapreduce \
  -param INPUT="$HDFS_BASE/vaccinations/data.csv" \
  -param OUTPUT="$HDFS_BASE/missed_doses" \
  native/etl_imunisasi.pig

hdfs dfs -cat "$HDFS_BASE/missed_doses/part-*"
```

Setiap eksekusi Pig membutuhkan output yang belum ada; gunakan namespace dari run Hadoop baru untuk pengulangan. `setup_hive.hql` mengarahkan ulang external table di database **khusus demo** `modul4_demo` ke namespace saat ini. Pig menggunakan input yang sama dengan Hive; pada paket ini keduanya merupakan cabang terpisah, bukan hasil Pig yang otomatis dibaca Hive.

Contoh HBase untuk tabel demo baru, sekali saja:

```bash
hbase shell native/hbase_lookup.hbase
```

Jika tabel tersebut sudah ada, jalankan baris `put` dan `get` di HBase Shell tanpa mengulang `create`. Ini memasukkan satu anak contoh, bukan pipeline bulk import dari Hive/Pig.

**Status:** perintah native disediakan berdasarkan dokumentasi Apache, tetapi belum dieksekusi atau divalidasi di cluster. Keberhasilan demo lokal tidak membuktikan koneksi HDFS/YARN/Hive/Pig/HBase.

## Rujukan tambahan untuk kode

- [Hadoop Streaming](https://hadoop.apache.org/docs/stable/hadoop-streaming/HadoopStreaming.html): stdin/stdout, key/value, dan generic options sebelum opsi streaming.
- [Hive DDL](https://hive.apache.org/docs/latest/language/languagemanual-ddl/): external tables dan lokasi data.
- [Pig Latin Basics](https://pig.apache.org/docs/r0.17.0/basic.html): LOAD, FILTER, FOREACH, STORE.
- [HBase Reference Guide](https://hbase.apache.org/book.html#quickstart): HBase Shell dan akses berdasarkan row key.
- [Sqoop di Apache Attic](https://attic.apache.org/projects/sqoop.html) dan [Oozie di Apache Attic](https://attic.apache.org/projects/oozie.html): keduanya telah retired. Tetap dibahas sesuai modul sebagai konteks ekosistem; jangan otomatis memilihnya untuk proyek produksi baru.

## Mengatur jumlah anak dan provinsi

Generator sekarang menerima jumlah anak dan provinsi. Perintah ini membuat ulang sumber menjadi 80.137 anak, 12 provinsi Indonesia, dan 24 kabupaten (dua kabupaten per provinsi):

```powershell
python code/prepare_dummy_dataset.py --children 80137 --provinces 12
```

Setiap anak memiliki ID unik. Pola dosis tetap mudah diikuti. Jumlah anak dibagi hampir merata ke kelompok kabupaten/tahun lahir, lalu diberi variasi tetap hingga tiga anak per kelompok tanpa mengubah total. Jumlah penerima dosis dibuat berbeda untuk tiap kabupaten. Sebanyak 50 profil awal tiap kelompok mempertahankan contoh sederhana; profil berikutnya mengikuti jumlah dosis yang ditetapkan. Dataset utama sengaja memiliki 24 persentase cakupan D3 dan 23 persentase putus lanjut numerik yang berbeda. Kabupaten Semarang mempertahankan D1=0 sehingga putus lanjutnya N/A. Data tetap skenario buatan, bukan keragaman populasi nyata. Tanggal dosis dan profil tetap diperiksa agar konsisten. Nama wilayah mengikuti katalog `code/indonesia_regions.py`; rujukan nama dan pasangan provinsi/kabupaten ada di [source/regions/README.md](source/regions/README.md). Default memakai dua kabupaten dari setiap provinsi pilihan, bukan seluruh kabupaten Indonesia. Opsi hingga 38 provinsi memakai kabupaten/kota contoh; DKI Jakarta mencakup kota administrasi.

Setelah mengganti ukuran, jalankan `python code/demo.py storage` untuk memulai sesi baru, kemudian jalankan tahap lain. Untuk memperbarui angka halaman, jalankan `python code/build_presentation_demo.py` lalu refresh browser.

Untuk latihan cepat dengan sampel kecil, gunakan `python code/prepare_dummy_dataset.py --children 1200 --provinces 3`, lalu mulai storage baru dan bangun ulang halaman. Tanpa opsi, generator memakai 80.137 anak dan 12 provinsi. Rentang yang diterima: 1.200–1.000.000 anak dan 1–38 provinsi. Pilihan ini adalah batas konfigurasi generator; pengujian saat ini memakai 1.200 dan 80.137 anak.

Untuk memastikan tiap provinsi memiliki dua kabupaten dan empat kelompok tahun lahir, jumlah anak minimal adalah 400 × jumlah provinsi (serta minimal total 1.200 anak). Contoh 38 provinsi membutuhkan paling sedikit 15.200 anak.
