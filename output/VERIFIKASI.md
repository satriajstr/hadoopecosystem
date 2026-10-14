# Verifikasi dataset utama — 12 Oktober 2026

Ringkasan berikut merujuk hasil pemeriksaan yang tersimpan di [verification.json](presentation/verification.json), [verifikasi pembesaran dataset](presentation/scale_verification.json), dan [review konsep](REVIEW_KONSEP.md). Panduan manual utama: [DEMO_MANUAL_WINDOWS.md](../DEMO_MANUAL_WINDOWS.md).

| Bagian | Hasil tercatat |
|---|---|
| Dataset utama | 80.137 anak sintetis, 12 provinsi, 24 kabupaten bernama asli Indonesia; 112.931 catatan dosis |
| Kelompok analisis | 20.035 anak kohort 2023 yang memenuhi syarat; 10.655 sudah D3 dan 9.380 belum D3 |
| Penyimpanan dan pemulihan | 962 blok, dua salinan per blok; pembacaan setelah DN1 gagal cocok dengan sumber; 641 blok mendapat salinan pengganti |
| MapReduce dan SQL | Hasil penghitungan per kabupaten cocok |
| Eksplorasi Hive | Top 5 tertinggi/terendah, top 10, keseluruhan, dan per provinsi diperiksa; putus lanjut keseluruhan 26,37%, cakupan D3 53,18% |
| Tindak lanjut Pig/HBase | 3.816 putus lanjut dan 5.564 belum memulai D1; 300 putus lanjut Jember; ID D016716 dari daftar ditemukan melalui HBase |
| Alokasi tugas | Eksekusi mapper paralel, antrean ketika kapasitas terbatas, dan pelepasan kapasitas diperiksa |
| Lookup | Profil dan riwayat `D000030`, Kabupaten Bandung, Jawa Barat; pemisahan kelompok kolom diperiksa |
| Pemeriksaan otomatis | 10 uji registri, 6 uji model konsep, dan 4 uji latihan dasar lulus |
| Struktur halaman utama | Delapan bagian dan 15 tautan file diperiksa; tampilan browser versi ini belum diperiksa |

Nama wilayah asli tidak menjadikan status dosis atau persentase demo sebagai data kesehatan nyata. Hasil tercatat berasal dari demo Python/SQLite di Windows; eksekusi native belum diuji. Sesi bukti dasar: `manual-demo/runs/20261012-175331-ionxdp8d/`. [Verifikasi eksplorasi terbaru](presentation/exploration_verification.json) memakai sesi CLI terpisah agar sesi aktif pengguna tetap sama. Dataset berisi 80.137 anak; kuota penerima dosis divariasikan per kabupaten, kemudian peragaan dasar dan eksplorasi Hive/Pig diperiksa ulang pada 12 Oktober 2026.

## Arsip verifikasi latihan dasar — 6 Oktober 2026

Bagian di bawah hanya merujuk dataset lama 21 anak dan halaman `demo_report.html`, bukan halaman presentasi utama atau registri 80.137 anak.

| Bagian | Hasil | Bukti |
|---|---|---|
| Mapper/reducer lokal | Lulus | Proses Python aktual, output `wordcount.tsv` |
| Word Count | Lulus | hadoop=3, hive=3, hdfs=1, pig=1, yarn=1 |
| Lab query students | Lulus di SQLite | Ani 3.8, Citra 3.5, Eka 3.2 |
| ETL lokal | Lulus | 21 baris → 18 eligible → 11 belum dosis 3 |
| SQL cakupan/dropout | Lulus di SQLite | `coverage.csv`; Selatan dropout NULL/N/A |
| Lookup A004 lokal | Lulus | `case_results.json`; dose1=1, dose3=0 |
| Pemeriksaan otomatis | 4 test lulus | `python code/test_demo.py`; termasuk input kosong, kelompok terakhir, denominator nol, duplikat/invalid, dan batas GPA |
| Tampilan HTML | Ditinjau | Halaman dimuat di browser lokal; kartu Selatan dan Utara terlihat dan terbaca |
| HDFS/YARN/Hadoop Streaming native | Belum dijalankan | Lingkungan cluster belum tersedia |
| Hive/Pig/HBase native | Belum dijalankan | Kode disediakan; bukan bukti keberhasilan integrasi |

Dataset seluruhnya sintetis. Tidak ada pengukuran skala jutaan baris, fault tolerance, atau prediksi wabah. Query native memakai skema yang sesuai data demo; compatibility/runtime cluster tetap perlu dry run di lingkungan lab.
