# Hasil double-check konsep demo Modul 4

Tanggal pemeriksaan: 12 Oktober 2026. Fokus: ketepatan peragaan konsep Hadoop Ecosystem dan studi kasus registri imunisasi dengan Python/SQLite di Windows.

## Kesimpulan

Perhitungan dan alur analisis dasar benar. Dataset per anak beserta event dosis mendukung analisis lintas provinsi/kabupaten, pemilihan kohort, dosis terlewat, dan lookup riwayat individual. Temuan audit awal telah ditindaklanjuti: peragaan kini menjalankan blok/replika dan pemulihan DataNode, alokasi container YARN yang mengatur eksekusi tugas, serta pemetaan kolom HBase. Detail implementasi tetap merupakan model pembelajaran Python/SQLite.

Nama komponen boleh menjadi judul tahap pembelajaran. Hasil yang ditampilkan harus sesuai mekanisme yang benar-benar diperagakan; jangan menambahkan angka throughput, log alokasi, waktu job, atau keberhasilan pemulihan yang tidak dihasilkan oleh kode.

## Pemeriksaan per komponen

| Komponen | Yang sudah tepat | Yang perlu dilengkapi |
|---|---|---|
| HDFS | File menjadi 962 blok byte dengan faktor replika 2 di tiga DataNode. Client membaca lokasi dari metadata lalu byte dari DataNode. DN1 OFFLINE; pembacaan berhasil dan 641 blok mendapat replika pengganti. | Blok 16 KiB, penempatan bergilir, dan hash SHA-256 adalah pilihan model pembelajaran. Rack awareness, jaringan, heartbeat berkala, dan HA tidak menjadi fokus. Hash dipusatkan di manifest untuk penelusuran; pada HDFS checksum diverifikasi melalui client/DataNode. |
| MapReduce | Dua input logis masuk ke mapper; pasangan key/value dikelompokkan melalui shuffle/sort lalu dijumlahkan reducer. Key mencakup provinsi dan kabupaten agar nama kabupaten tidak tercampur. Hasil cocok dengan SQL. | Jelaskan bahwa input split adalah pembagian logis untuk mapper, berbeda dari blok penyimpanan HDFS. Satu reducer cukup untuk contoh ini; beberapa reducer dan partitioner merupakan pengayaan. |
| YARN | ResourceManager mengalokasikan container, NodeManager menjalankan task, ApplicationMaster meminta resource. Dua mapper berjalan bersamaan dengan tiga NodeManager; opsi dua NodeManager menunjukkan antrean. Reducer berjalan setelah map/shuffle, resource dilepas, dan status aplikasi mengikuti keberhasilan/kegagalan tugas. | CPU/RAM adalah unit anggaran logis yang mengatur dispatch; bukan pembatasan OS atau pengukuran RAM host. Scheduler memodelkan alokasi sederhana tanpa queue prioritas, data locality, restart AM, atau retry task. |
| Hive | SQL memilih kohort eligible dan mengagregasi cakupan/dropout per wilayah; pembagian nol ditangani. Padanan external table dan lokasi input tersedia. | Tegaskan tabel/schema mengacu pada file input. Hive tidak wajib memakai MapReduce pada setiap konfigurasi. |
| Pig | Alur load → filter kohort → filter dosis terlewat → store sesuai ETL kasus modul. | Untuk kebutuhan presentasi ini alur dasar sudah cukup. Daftar dosis terlewat lebih luas daripada dropout: anak yang belum D1 juga bisa belum D3. |
| HBase | Row key berupa child_id; terminal dan CSV menunjukkan family profile/history, qualifier, serta value. Lookup konsisten dengan event sumber dan ID hasil ETL. ID tidak ditemukan dibedakan dari riwayat kosong. | Timestamp versi sel, RegionServer, WAL, compaction, dan distribusi region tidak menjadi fokus. Tanggal vaksinasi pada value berbeda dari timestamp versi sel HBase. |

## Pemeriksaan hasil dan denominator

- Sumber: 80.137 anak, 12 provinsi, 24 kabupaten, 112.931 event dosis. Nama wilayah asli Indonesia; data imunisasi sintetis, bukan kondisi sebenarnya di wilayah tersebut. Semua 24 pasangan kabupaten/provinsi cocok dengan rujukan BPS pada source/regions/.
- Kohort analisis: kelahiran 2023 dan dose3_due=1, sebanyak 20.035 anak.
- Penerima D1: 14.471 anak. Penerima D3: 10.655 anak. Belum D3: 9.380 anak.
- Cakupan D3 = penerima D3 / seluruh anak eligible dalam kohort × 100%.
- Dropout D1→D3 = (penerima D1 − penerima D3) / penerima D1 × 100%.
- D1=0 menghasilkan dropout NULL/N/A, bukan 0%.
- D000030 masuk daftar belum D3 dan lookup-nya sesuai sumber event: DTP1 tanggal 2023-06-01, DTP2 tanggal 2023-07-01.
- Eligibility dan tanggal merupakan asumsi dataset pembelajaran. Status 0 berarti belum menerima dalam dataset ini; data operasional perlu membedakan belum menerima dan status tidak diketahui.

## Kesesuaian studi kasus dan 5V

Analisis cakupan/dropout, ETL kohort/dosis terlewat, serta lookup individual sudah terwakili. Aturan cakupan <80% hanya aturan prioritas contoh. Analisis ini belum memprediksi wabah; prediksi membutuhkan definisi target, data tambahan, model, dan validasi.

| Aspek | Posisi demo saat ini |
|---|---|
| Volume | Sampel kecil untuk menelusuri mekanisme; belum memperagakan jutaan rekaman atau perilaku pada skala besar. |
| Velocity | Satu snapshot batch. Laju masuk dan pembaruan berkala belum diperagakan. |
| Variety | Ada profil anak dan event dosis dengan schema berbeda. Mengonversi sumber sama ke CSV/TSV/JSON saja tidak membuktikan keragaman sumber data. |
| Veracity | Validasi ID, konsistensi profil/event, urutan dosis/tanggal, dan hash membantu menunjukkan kualitas data. Data tetap sintetis. |
| Value | Hasil menemukan wilayah dengan cakupan rendah dan anak yang belum menerima D3, sehingga mendukung contoh tindak lanjut. |

5V adalah karakteristik masalah dan data, bukan lima syarat yang otomatis terpenuhi karena memakai nama tool Hadoop. Tidak perlu membesarkan dataset hanya untuk memperbaiki penjelasan konsep.

## Alur integrasi dan prioritas penyempurnaan

Input registri menjadi sumber bersama untuk agregasi MapReduce/Hive, ETL Pig, dan pemuatan data lookup HBase. Hasil daftar dosis terlewat dapat digunakan untuk memilih ID yang riwayatnya diperiksa. Cabang-cabang ini valid; tidak wajib menjadikan semua komponen satu rantai linear.

Penyempurnaan yang telah dilakukan:

1. Peragaan blok, replika, metadata, pembacaan saat satu DataNode gagal, dan re-replikasi.
2. Peragaan alokasi container YARN dan siklus aplikasi yang mengikuti eksekusi mapper/reducer; opsi antrean dengan dua NodeManager.
3. Contoh kolom HBase dan diagram cabang analisis/ETL/lookup. Sqoop, Flume, dan Oozie dijelaskan melalui tabel perannya.

Tidak diperlukan VM atau layanan tambahan untuk memperagakan mekanisme tersebut. Demo tetap memakai dataset dan antarmuka perintah yang sama; setiap percobaan mempunyai folder hasil baru.

## Bukti pemeriksaan

- Dibaca: README.md, PANDUAN_PRESENTASI.md, kode demo.py, mapper/reducer registri, builder presentasi, dan padanan kode pada native/registry/.
- code/test_registry_demo.py: 10 pengujian lulus, termasuk rujukan 24 wilayah Indonesia, konfigurasi 38 provinsi, ukuran/provinsi yang dapat diatur, konsistensi dataset, agregasi, lookup, input invalid, reducer, pengulangan sesi, ranking dengan denominator nol, persentase keseluruhan dari total jumlah anak, dan pemisahan daftar tindak lanjut per wilayah.
- code/test_concept_models.py: 6 pengujian lulus: batas blok byte/UTF-8, replica failure dan repair, korupsi replika, seluruh replika hilang, file kosong, alokasi paralel/antrean, serta pelepasan resource saat task gagal.
- code/test_demo.py: 4 pengujian latihan dasar lulus.
- Penghitungan independen menghasilkan 20.035 eligible, 10.655 D3, dan 9.380 belum D3; denominator/pembulatan SQL untuk 24 kabupaten cocok. ID hasil ETL dan event sumber lookup konsisten.
- Pemeriksaan ini memverifikasi kode dan hasil, bukan penilaian terhadap rubrik dosen.

Eksplorasi Hive/Pig telah diperiksa melalui perintah CLI aktual dalam sesi terpisah: top 5 tertinggi/terendah, top 10, keseluruhan, per provinsi, penyaringan Jember, dan pencarian HBase dari ID hasil Pig. Bukti ada di [exploration_verification.json](presentation/exploration_verification.json). Putus lanjut seluruh sampel kohort 2023 adalah 3.816 / 14.471 = 26,37%; 9.380 belum D3 dipisahkan menjadi 3.816 putus lanjut dan 5.564 belum memulai D1. Sumber dataset dan sesi aktif tetap sama.

## Rujukan konsep resmi

- [Apache HDFS Architecture](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html): blok, metadata NameNode, DataNode, replikasi, dan pemulihan kegagalan.
- [Apache YARN Architecture](https://hadoop.apache.org/docs/r3.4.2/hadoop-yarn/hadoop-yarn-site/YARN.html): ResourceManager, NodeManager, ApplicationMaster, dan container resource.
- [Apache MapReduce Tutorial](https://hadoop.apache.org/docs/r3.4.2/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html): input split, mapper, shuffle/sort, dan reducer.
- [Hive Language Manual DDL](https://hive.apache.org/docs/latest/language/languagemanual-ddl/): schema, external table, dan lokasi input.
- [Pig Latin Basics](https://pig.apache.org/docs/r0.17.0/basic.html): LOAD, FILTER, dan STORE.
- [HBase Data Model](https://hbase.apache.org/book.html#datamodel): row key, column family, qualifier, value, dan timestamp versi.
