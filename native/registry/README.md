# Rancangan native untuk registri dummy

**NOT RUN.** Format utama proyek adalah Python/SQLite di Windows. File di sini merupakan padanan kode untuk menjelaskan komponen modul, bukan bukti Hadoop/Hive/Pig/HBase sudah berjalan.

Input mengikuti [dataset utama](../../data/dummy/README.md): 80.137 profil anak, 12 provinsi, 24 kabupaten, dan 112.931 catatan pemberian dosis. Nama wilayah asli Indonesia; catatan anak dan imunisasinya sintetis. Analisis memilih 20.035 anak kelahiran 2023 yang ditandai sudah waktunya menerima D3. Contoh lookup `D000030` berasal dari Kabupaten Bandung, Jawa Barat. Untuk demo manual Windows, ikuti [DEMO_MANUAL_WINDOWS.md](../../DEMO_MANUAL_WINDOWS.md).

| File | Peran |
|---|---|
| `mapreduce.sh` | Namespace HDFS baru, upload children.tsv, submit mapper/reducer melalui YARN |
| `setup_hive.hql` | External table sepuluh kolom dengan lokasi TSV registri |
| `coverage.sql` | Query cakupan/dropout kohort 2023; sudah diuji di SQLite |
| `analysis_overall.sql`, `analysis_province.sql` | Persentase keseluruhan dan per provinsi dari total jumlah anak |
| `analysis_highest.sql`, `analysis_lowest.sql` | Top 5 putus lanjut; D1=0 dikecualikan; nilai sama diurutkan berdasarkan wilayah |
| `etl.pig` | Kohort, daftar belum D3, daftar putus lanjut, dan daftar belum memulai D1 |
| `lookup.hbase` | Contoh put/get profil dan riwayat D000030; dibuat dari data dummy oleh builder |

Jika kelak memiliki cluster siap pakai, jalankan dari root proyek:

```bash
bash native/registry/mapreduce.sh
```

Script mencetak nilai aktual `HDFS_BASE`. Isi variabel terminal dengan nilai tersebut. Script menggunakan namespace baru pada setiap eksekusi; tidak memformat HDFS atau menghapus hasil sebelumnya.

```bash
export HDFS_BASE='SALIN_PATH_AKTUAL_YANG_DICETAK_SCRIPT'
beeline -u "$HIVE_JDBC_URL" \
  --hivevar registry_path="$HDFS_BASE/children" \
  -i native/registry/setup_hive.hql -f native/registry/coverage.sql
pig -x mapreduce \
  -param INPUT="$HDFS_BASE/children/children.tsv" \
  -param OUTPUT="$HDFS_BASE/registry-etl" \
  native/registry/etl.pig
```

Output Pig harus belum ada; untuk pengulangan gunakan namespace baru. Instalasi, versi kompatibel, autentikasi, metastore, HiveServer2, dan konfigurasi resource tetap diperlukan dan belum diuji.

Untuk tabel HBase demo baru:

```bash
hbase shell native/registry/lookup.hbase
```

Jalankan `create` sekali saja. Jika tabel sudah ada, gunakan baris `put`/`get` saja. Contoh ini memuat satu anak dan dua catatan dosis, bukan pipeline bulk import atau sinkronisasi seluruh registri. Lookup Python memuat seluruh data lokal ke dictionary dan juga tidak membuktikan performa HBase.
