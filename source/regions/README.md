# Rujukan nama wilayah Indonesia untuk demo

Nama wilayah asli digunakan agar penjelasan mudah diikuti. **Data anak, fasilitas,
tanggal dan status imunisasi tetap sintetis. Persentase hasil demo bukan kondisi
imunisasi sebenarnya pada wilayah yang disebut.** Pemilihan wilayah bukan sampel
representatif dan tidak mencakup seluruh kabupaten Indonesia.

## Dua belas provinsi pada konfigurasi default

| Provinsi | Kabupaten pertama | Kabupaten kedua |
|---|---|---|
| Jawa Barat | Kabupaten Bandung | Kabupaten Bogor |
| Jawa Tengah | Kabupaten Semarang | Kabupaten Banyumas |
| Jawa Timur | Kabupaten Malang | Kabupaten Jember |
| Banten | Kabupaten Tangerang | Kabupaten Serang |
| DI Yogyakarta | Kabupaten Sleman | Kabupaten Bantul |
| Bali | Kabupaten Badung | Kabupaten Gianyar |
| Sumatera Utara | Kabupaten Deli Serdang | Kabupaten Langkat |
| Sumatera Barat | Kabupaten Agam | Kabupaten Tanah Datar |
| Sumatera Selatan | Kabupaten Banyuasin | Kabupaten Ogan Komering Ilir |
| Lampung | Kabupaten Lampung Selatan | Kabupaten Lampung Tengah |
| Kalimantan Barat | Kabupaten Kubu Raya | Kabupaten Sambas |
| Sulawesi Selatan | Kabupaten Gowa | Kabupaten Maros |

Kabupaten Bandung berbeda dari Kota Bandung; Kabupaten Semarang berbeda dari
Kota Semarang. Awalan Kabupaten dipertahankan agar tidak ambigu.

## Sumber dan pemeriksaan

- [BPS SIRuSa, daftar provinsi/kabupaten pada metadata kegiatan statistik](https://sirusa.web.bps.go.id/metadata/kegiatan/2999f8ef-4f55-dcfc-0fdc-a06896d96644).
  Diunduh 11 Oktober 2026. Halaman sumber memiliki 457 pasangan untuk cakupan
  kegiatan tersebut; bukan master lengkap wilayah terkini. Semua 24 pasangan
  default dicocokkan dengan daftar tersebut. Ejaan `BANYU ASIN` dinormalisasi
  menjadi `Banyuasin`. Isi asli ada di `bps_region_reference.html`; pasangan
  yang diekstrak dan SHA-256 sumber ada di `bps_region_pairs.json`.
- [BPS: penduduk menurut kabupaten/kota dan kelompok umur](https://www.bps.go.id/en/statistics-table/2/Mjc5MCMy/jumlah-penduduk-menurut-kabupaten-kota-dan-kelompok-umur.html).
  Digunakan sebagai rujukan tambahan pengelompokan provinsi Papua hasil pemekaran.
- [BPS: wilayah Papua Barat Daya](https://papuabarat.bps.go.id/id/statistics-table/2/MzIxIzI%3D/population-by-regency-municipality-and-gender-in-papua-barat-daya-province.html).
- [BPS Paniai: wilayah Papua Tengah](https://paniaikab.bps.go.id/id/news/2025/05/20/24/luas-panen-padi-provinsi-papua-tengah-2024.html).

Sumber dipakai hanya untuk nama dan hubungan wilayah; angka statistik sumber
tidak digunakan untuk membangun anak atau dosis dummy. Katalog terpilih pada
`code/indonesia_regions.py` menjaga opsi generator hingga 38 provinsi, dua wilayah
per provinsi. Opsi yang mencakup DKI Jakarta memakai kota administrasi, sehingga
pada konfigurasi tersebut istilah wilayah adalah kabupaten/kota.

## Penggantian dataset

Urutan wilayah dipertahankan untuk menjaga ID, status dosis, tanggal, jumlah anak,
dan seluruh perhitungan demo. Contoh lama Utara diganti Kabupaten Bandung, Jawa
Barat. File CSV/TSV dan metadata dibuat ulang oleh generator, bukan penggantian
teks pada hasil analisis. Hasil analisis dan halaman presentasi dibangun ulang dari
input baru. Sesi demo lama tetap disimpan sebagai arsip percobaan.
