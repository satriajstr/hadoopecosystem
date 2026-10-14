# Registri imunisasi dummy — dataset utama demo

**Data imunisasi sintetis untuk pembelajaran, menggunakan nama wilayah asli Indonesia.** Dibuat oleh `code/prepare_dummy_dataset.py`. ID anak, fasilitas, tanggal, dan status dosis merupakan skenario pembelajaran. Nama kabupaten beserta provinsinya mengikuti wilayah Indonesia; hasil persentase bukan kondisi imunisasi sebenarnya di daerah tersebut. Data tidak diturunkan dari persentase WHO dan tidak mewakili populasi Indonesia.

## Isi dan grain

| File | Isi |
|---|---|
| `children.csv` | 80.137 profil; satu baris per anak |
| `children.tsv` | Profil yang sama tanpa header untuk mapper dan rancangan Hive/Pig |
| `vaccination_events.csv` | 112.931 catatan; satu baris per pemberian dosis DTP |
| `metadata.json` | Asumsi generator, jumlah record, dan SHA-256 tiap file |

12 provinsi Indonesia. masing-masing dua kabupaten. Jumlah anak per kabupaten berkisar 3.336–3.340 anak, dengan sedikit variasi pada tiap kelompok tahun lahir. Tahun lahir tetap 2022, 2023, 2024, dan 2025. Generator deterministik: parameter yang sama menghasilkan data yang sama.

## Kolom profil

`child_id`, `province`, `district`, `birth_date`, `birth_year`, `dose3_due`, `dose1`, `dose2`, `dose3`, `last_updated`.

- `child_id` unik dan menjadi key lookup.
- `dose1`/`dose2`/`dose3`: 1 = sudah menerima, 0 = belum menerima dalam skenario. Status unknown tidak ada pada sampel ini; jangan menyamakan missing pada data nyata dengan 0.
- `dose3_due`: flag eligibility **buatan** untuk demo. Tahun 2022–2024 diberi 1; tahun 2025 diberi 0. Analisis utama tetap memilih **kohort 2023** dan due=1, bukan semua tahun eligible.
- `last_updated`: tanggal snapshot fiktif 2026-10-01.

Kolom event: `child_id`, `vaccine`, `dose_number`, `vaccination_date`, `facility_id`. Tanggal dibuat berurutan, bukan jadwal vaksinasi yang direkomendasikan. Profil berstatus 1 hanya jika event dosis yang sesuai tersedia; satu anak/dosis hanya boleh memiliki satu event.

## Skenario analisis kohort 2023

| Provinsi | Kabupaten | Memenuhi syarat | D1 | D3 | Cakupan D3 | Putus lanjut |
|---|---|---:|---:|---:|---:|---:|
| Jawa Tengah | Kabupaten Semarang | 832 | 0 | 0 | 0.00% | N/A |
| DI Yogyakarta | Kabupaten Sleman | 832 | 81 | 11 | 1.32% | 86,42% |
| Kalimantan Barat | Kabupaten Kubu Raya | 831 | 94 | 22 | 2.65% | 76,60% |
| Sumatera Barat | Kabupaten Agam | 832 | 90 | 27 | 3.25% | 70,00% |
| Bali | Kabupaten Gianyar | 838 | 572 | 256 | 30.55% | 55,24% |
| Sumatera Selatan | Kabupaten Ogan Komering Ilir | 838 | 572 | 259 | 30.91% | 54,72% |
| Sulawesi Selatan | Kabupaten Maros | 837 | 572 | 261 | 31.18% | 54,37% |
| Jawa Timur | Kabupaten Jember | 838 | 573 | 273 | 32.58% | 52,36% |
| Jawa Barat | Kabupaten Bandung | 832 | 747 | 419 | 50.36% | 43,91% |
| Banten | Kabupaten Tangerang | 832 | 747 | 422 | 50.72% | 43,51% |
| Sumatera Utara | Kabupaten Deli Serdang | 832 | 747 | 424 | 50.96% | 43,24% |
| Lampung | Kabupaten Lampung Selatan | 832 | 747 | 427 | 51.32% | 42,84% |
| Sumatera Selatan | Kabupaten Banyuasin | 832 | 654 | 503 | 60.46% | 23,09% |
| Sulawesi Selatan | Kabupaten Gowa | 831 | 653 | 505 | 60.77% | 22,66% |
| Jawa Timur | Kabupaten Malang | 832 | 654 | 517 | 62.14% | 20,95% |
| Bali | Kabupaten Badung | 832 | 654 | 519 | 62.38% | 20,64% |
| Jawa Barat | Kabupaten Bogor | 838 | 750 | 677 | 80.79% | 9,73% |
| Banten | Kabupaten Serang | 838 | 750 | 680 | 81.15% | 9,33% |
| Sumatera Utara | Kabupaten Langkat | 838 | 750 | 682 | 81.38% | 9,07% |
| Lampung | Kabupaten Lampung Tengah | 837 | 749 | 684 | 81.72% | 8,68% |
| Jawa Tengah | Kabupaten Banyumas | 838 | 829 | 768 | 91.65% | 7,36% |
| DI Yogyakarta | Kabupaten Bantul | 838 | 829 | 771 | 92.00% | 7,00% |
| Sumatera Barat | Kabupaten Tanah Datar | 838 | 829 | 773 | 92.24% | 6,76% |
| Kalimantan Barat | Kabupaten Sambas | 837 | 828 | 775 | 92.59% | 6,40% |

Total kohort: **20.035 anak eligible, 10.655 menerima D3, 9.380 belum D3**. Anak yang belum memulai D1 tetap masuk denominator cakupan. Dropout memakai penerima D1 sebagai denominator; saat D1=0, nilainya N/A.

Aturan prioritas `coverage < 80%` dipilih sebagai contoh untuk demonstrasi. Bukan ambang klinis dan bukan model prediksi wabah. Sampel ini belum memenuhi volume jutaan rekaman, streaming, atau seluruh ragam sumber big data.

## Lookup contoh

`D000030`, Jawa Barat/Kabupaten Bandung, lahir 2023-01-02. DTP1 tercatat 2023-06-01, DTP2 2023-07-01, DTP3 belum diterima. `D000046` ditemukan sebagai profil tetapi belum memiliki riwayat dosis. ID yang tidak ada dilaporkan sebagai **tidak ditemukan**, bukan profil tanpa dosis.

## Membuat ulang dan menjalankan

```powershell
python code/prepare_dummy_dataset.py
python code/demo.py all
python code/test_registry_demo.py
python code/build_presentation_demo.py
```

Demo manual: [`DEMO_MANUAL_WINDOWS.md`](../../DEMO_MANUAL_WINDOWS.md). Peragaan menggunakan Python/SQLite di Windows untuk menunjukkan alur Hadoop Ecosystem. Dataset WHO tetap berada di `data/real/` sebagai contoh agregat nasional terpisah.

## Mengatur jumlah anak dan provinsi

Generator sekarang menerima jumlah anak dan provinsi. Perintah ini membuat ulang sumber menjadi 80.137 anak, 12 provinsi Indonesia, dan 24 kabupaten (dua kabupaten per provinsi):

```powershell
python code/prepare_dummy_dataset.py --children 80137 --provinces 12
```

Setiap anak memiliki ID unik. Pola dosis tetap mudah diikuti. Jumlah anak dibagi hampir merata ke kelompok kabupaten/tahun lahir, lalu diberi variasi tetap hingga tiga anak per kelompok tanpa mengubah total. Jumlah penerima dosis dibuat berbeda untuk tiap kabupaten. Sebanyak 50 profil awal tiap kelompok mempertahankan contoh sederhana; profil berikutnya mengikuti jumlah dosis yang ditetapkan. Dataset utama sengaja memiliki 24 persentase cakupan D3 dan 23 persentase putus lanjut numerik yang berbeda. Kabupaten Semarang mempertahankan D1=0 sehingga putus lanjutnya N/A. Data tetap skenario buatan, bukan keragaman populasi nyata. Tanggal dosis dan profil tetap diperiksa agar konsisten. Nama wilayah mengikuti katalog `code/indonesia_regions.py`; rujukan nama dan pasangan provinsi/kabupaten ada di [rujukan wilayah](../../source/regions/README.md). Default memakai dua kabupaten dari setiap provinsi pilihan, bukan seluruh kabupaten Indonesia. Opsi hingga 38 provinsi memakai kabupaten/kota contoh; DKI Jakarta mencakup kota administrasi.

Setelah mengganti ukuran, jalankan `python code/demo.py storage` untuk memulai sesi baru, kemudian jalankan tahap lain. Untuk memperbarui angka halaman, jalankan `python code/build_presentation_demo.py` lalu refresh browser.

Untuk latihan cepat dengan sampel kecil, gunakan `python code/prepare_dummy_dataset.py --children 1200 --provinces 3`, lalu mulai storage baru dan bangun ulang halaman. Tanpa opsi, generator memakai 80.137 anak dan 12 provinsi. Rentang yang diterima: 1.200–1.000.000 anak dan 1–38 provinsi. Pilihan ini adalah batas konfigurasi generator; pengujian saat ini memakai 1.200 dan 80.137 anak.

Untuk memastikan tiap provinsi memiliki dua kabupaten dan empat kelompok tahun lahir, jumlah anak minimal adalah 400 × jumlah provinsi (serta minimal total 1.200 anak). Contoh 38 provinsi membutuhkan paling sedikit 15.200 anak.
