# Dataset nyata untuk studi kasus imunisasi

**Pelengkap terpisah.** Demo utama memakai registri dummy per anak di [`data/dummy/`](../dummy/README.md). Halaman WHO tersimpan di `output/who-presentation/index.html`; panduan manualnya [`DEMO_MANUAL_WHO_WINDOWS.md`](../../DEMO_MANUAL_WHO_WINDOWS.md).

**Sumber:** WHO/UNICEF Estimates of National Immunization Coverage (WUENIC), **2025 revision**, diperoleh melalui API publik resmi UNICEF pada 7 Oktober 2026. Halaman sumber: [Immunization data](https://data.unicef.org/resources/dataset/immunization/). Dokumentasi API: [UNICEF SDMX](https://data.unicef.org/sdmx-api-documentation/).

## File dan grain

| File | Isi |
|---|---|
| `immunization_coverage_long.csv` | 20.032 observasi; satu baris = wilayah/kelompok × indikator × sex × tahun |
| `immunization_coverage_long.tsv` | Data yang sama, tanpa header, untuk external table Hive |
| `indonesia_dtp_long.csv` | 90 observasi Indonesia, DTP1/DTP3, 1981–2025 |
| `../../source/real/unicef_dtp1_dtp3_1980_2025.json` | Respons API asli, termasuk struktur dan metadata |
| `../../source/real/provenance.json` | URL sumber, waktu penyimpanan snapshot lokal, dan SHA-256 |
| `../../output/real/indonesia_coverage_dropout.csv` | Hasil query per tahun Indonesia, dieksekusi dengan SQLite lokal |
| `../../output/real/quality_checks.json` | Pemeriksaan data dan rincian pasangan bermasalah |
| `../../code/real_dataset_checks.ipynb` | Notebook pendamping untuk meninjau dan mengulang pemeriksaan; belum dieksekusi melalui kernel Jupyter |

296 `REF_AREA` pada snapshot **mencakup negara dan kelompok agregat**, bukan 296 negara. Subset Indonesia sebelumnya tetap disimpan. Demo manual WHO memilih **IDN, MYS, THA, VNM, PHL**, **2020–2025**, saat pemrosesan input internasional lengkap; kelompok regional/global tidak ikut. Hasil: 30 observasi DTP3 untuk lima mean dan 60 observasi DTP1/DTP3 untuk 30 kelompok negara–tahun. Panduan: [`DEMO_MANUAL_WHO_WINDOWS.md`](../../DEMO_MANUAL_WHO_WINDOWS.md). Data sumber seluruh wilayah mencakup 1980–2025; data Indonesia yang tersedia mulai 1981. Tahun yang tidak ada tidak dibuat menjadi nol.

## Kolom

| Kolom | Arti |
|---|---|
| `area_code` | Kode wilayah sumber; Indonesia = IDN |
| `area_name` | Nama wilayah/kelompok sesuai sumber |
| `indicator` | IM_DTP1 = dosis pertama; IM_DTP3 = dosis ketiga |
| `sex` | _T = total sesuai sumber |
| `year` | Tahun pengukuran |
| `coverage_pct` | Estimasi cakupan dalam persen; bukan jumlah anak |
| `unit` | PCNT = persen |
| `observation_status` | E = estimated value |
| `source_revision` | Revisi WUENIC yang menerbitkan observasi |
| `age_group` | Metadata AGE asli; snapshot ini menerbitkan M12T23 |

Nama indikator sumber menyebut **surviving infants**; atribut AGE yang diterbitkan API adalah `M12T23`. Keduanya dipertahankan apa adanya. Metadata ini tidak menyediakan tanggal lahir atau eligibility individu dan tidak boleh digunakan untuk merekonstruksi kohort anak.

## Pemeriksaan yang sudah dilakukan

- Tidak ditemukan duplicate key `(area_code, indicator, sex, year)`.
- Tidak ditemukan nilai coverage kosong atau di luar 0–100.
- Unit seluruh observasi adalah PCNT, status E, dan source revision 2025.
- Ditemukan **2 pasangan wilayah/tahun tanpa kedua indikator** serta **6 pasangan dengan DTP3 > DTP1** pada data seluruh wilayah/kelompok. Rinciannya disimpan di `output/real/quality_checks.json`; nilainya tidak dikoreksi atau dibuang dari CSV sumber.
- Subset Indonesia mempunyai **45 tahun berpasangan**. Query tidak menghitung proxy dropout jika salah satu indikator tidak ada, DTP1 nol, atau DTP3 lebih besar daripada DTP1.

Nilai persentase yang valid bukan jaminan bahwa semua perbandingan valid. Penyebab enam pasangan DTP3 > DTP1 belum ditetapkan; jangan menafsirkan hasil negatif sebagai dropout tanpa meninjau metadata dan metodologi sumber.

## Contoh nyata yang sudah dihitung

Indonesia tahun **2025**: estimasi DTP1 **85%**, DTP3 **82%**. Selisihnya **3 poin persentase**. Proxy dropout agregat:

```text
(DTP1_pct - DTP3_pct) / DTP1_pct × 100
= (85 - 82) / 85 × 100
= 3,53%
```

Ini perhitungan dari estimasi cakupan dengan unit dan metadata yang sama. Angka tersebut **bukan pengukuran langsung terhadap anak yang sama**, bukan selisih 3%, dan bukan bukti identitas anak yang melewatkan dosis. Nilai cakupan diterbitkan sebagai estimasi, sehingga digit desimal hasil perhitungan tidak menyatakan akurasi klinis tambahan.

## Mulai praktik di PowerShell

```powershell
Get-Content .\data\real\indonesia_dtp_long.csv -TotalCount 7
python code/prepare_real_dataset.py
```

Default memakai snapshot lokal agar praktik dapat diulang tanpa internet. Untuk sengaja mengganti snapshot dengan respons API terbaru:

```powershell
python code/prepare_real_dataset.py --refresh
```

Unduhan Excel resmi mengembalikan HTTP 403 pada pemeriksaan ini. Data berhasil diperoleh melalui API publik resmi yang didokumentasikan UNICEF; tidak menggunakan mirror pihak ketiga atau mengisi nilai secara manual.

## Menggunakan data yang sama di Hive asli

Setelah HDFS dan HiveServer2 tersedia, jalankan di root proyek pada Linux/VM lab:

```bash
HDFS_REAL="/user/$(id -un)/modul4-real-$(date +%Y%m%d-%H%M%S)-$$"
hdfs dfs -mkdir -p "$HDFS_REAL"
hdfs dfs -put data/real/immunization_coverage_long.tsv "$HDFS_REAL/"

# Isi HIVE_JDBC_URL sesuai konfigurasi lab.
beeline -u "$HIVE_JDBC_URL" --hivevar hdfs_real="$HDFS_REAL" \
  -i native/real_setup_hive.hql -f native/real_immunization.sql
```

Perintah Hive/HDFS ini belum dieksekusi di cluster. Keberhasilan parser dan query SQLite lokal tidak membuktikan Hadoop/YARN atau Hive berjalan.

## Kecocokan dengan kasus di modul

**Bisa dibuktikan dengan dataset ini:** ETL dari sumber publik, validasi, filter Indonesia, tren cakupan DTP, dan indikator dropout agregat nasional. Dataset yang sama dapat dimasukkan ke HDFS dan diquery dengan Hive pada lingkungan yang sesuai.

**Belum didukung:** identifikasi kabupaten kurang terimunisasi, ekstraksi kohort kelahiran individu, daftar anak yang melewatkan dosis, lookup riwayat anak melalui HBase, prediksi wabah, dan performa jutaan record. Untuk itu diperlukan data dengan grain/atribut yang tepat dan, untuk prediksi/performa, pengujian tambahan. Lookup HBase pada data ini hanya bisa diadaptasi ke row key seperti `IDN:2025`, bukan ID anak.

Jangan memperbanyak baris atau membuat rekam anak dari persentase lalu menyebutnya dataset nyata. [Registri sintetis utama](../dummy/README.md) dibuat terpisah untuk menunjukkan profil anak, analisis per kabupaten, dan riwayat dosis; bukan rekonstruksi dari persentase WHO.
