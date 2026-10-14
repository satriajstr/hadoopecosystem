# Lingkungan Hadoop baru di laptop

**Opsi lingkungan lama, terpisah dari demo utama.** Presentasi saat ini memakai Python/SQLite di Windows dan dataset registri 80.137 anak; ikuti [panduan manual utama](../../DEMO_MANUAL_WINDOWS.md). VM di bawah tidak diperlukan untuk menjalankan demo tersebut. Catatan persiapan dan kebutuhan host di dokumen ini berasal dari pemeriksaan awal; lihat file status sebelum memakai VM.

Satu VM Ubuntu 22.04 di VirtualBox yang sudah terpasang. VM bernama **HadoopEcosystem-Modul4**, dialokasikan 6 GB RAM dan 4 vCPU. Disk dinamis maksimum 32 GB, bukan langsung menghabiskan 32 GB. Semua berkas VM, image, seed cloud-init, SSH key dan log disimpan di root proyek. VM eNSP yang sudah ada tidak digunakan.

Pembersihan 12 Oktober 2026 menghapus image instalasi `.vmdk` dari folder proyek dengan memindahkannya ke Recycle Bin. Disk VM `hadoop-lab.vdi`, seed, kunci SSH, dan konfigurasi VM tetap disimpan. Perintah `prepare` akan mengunduh image lagi jika dijalankan; untuk membuat seed ulang, pasang kembali dependency sementara dengan perintah di bawah.

Komponen lab: OpenJDK 8, Hadoop 3.3.6, Hive 4.0.1, Pig 0.18.0. Versi dipatok untuk kompatibilitas dan pengulangan demo. Ini lab lokal untuk modul, bukan rancangan produksi. HDFS menggunakan satu DataNode dan replication=1. Hive memakai MapReduce agar tidak perlu menambahkan Tez; engine ini deprecated di Hive 4. Derby embedded cukup untuk satu HiveServer2 dalam lab ini.

## Status dan kebutuhan host

`prepare` hanya mengunduh image, memverifikasi SHA256 dari Ubuntu, menyiapkan seed dan mendaftarkan VM; belum memasang Hadoop di guest. Instalasi paket berlangsung pada boot pertama: Hadoop diperiksa SHA512, Hive SHA256, dan Pig dengan signature PGP serta KEYS resmi Apache. Status aktual host/VM ada di `output/environment/host-status.json`; keberhasilan Hadoop ditentukan setelah HDFS, YARN dan Beeline diuji.

Saat pemeriksaan awal, RAM host bebas kurang dari 1 GB. Launcher menolak boot sampai tersedia **8 GiB RAM bebas**, untuk VM 6 GB dan ruang host. Instalasi pertama juga memerlukan setidaknya **10 GiB disk bebas setelah persiapan**. Tutup aplikasi yang tidak dipakai sebelum boot. Script tidak menghentikan aplikasi lain.

Pada boot berikutnya launcher mempertahankan minimal 4 GiB disk bebas. Jika instalasi awal terputus, pastikan masih ada ruang untuk sisa unduhan dan ekstraksi sebelum melanjutkannya; marker first-start belum berarti instalasi selesai.

## Dari PowerShell di root proyek

```powershell
python native/environment/manage_vm.py status
python native/environment/manage_vm.py prepare
python native/environment/manage_vm.py start
```

Jika mempersiapkan ulang pada mesin baru, dependency pembuat seed ISO dipasang hanya di folder sementara proyek:

```powershell
python -m pip install --target tmp/vm-tools pycdlib==1.16.0
```

Boot pertama memerlukan internet untuk apt dan arsip resmi Apache. Waktu instalasi tergantung unduhan, dapat jauh lebih lama dari durasi demo. Siapkan dan uji **sebelum** presentasi.

```powershell
python native/environment/manage_vm.py ssh
```

Jika SSH belum tersedia, tunggu boot lalu ulangi. Setelah masuk VM:

```bash
tail -n 30 ~/install.log
sudo cloud-init status --long
test -f ~/lab/state/install.ready && echo 'Instalasi paket selesai'
```

Jangan menjalankan ulang installer selama cloud-init masih mengerjakan instalasi. Jika gagal, periksa `~/install.log`, `~/lab/logs/install.log` dan `/var/log/cloud-init-output.log`. Installer dapat dijalankan ulang setelah proses sebelumnya berhenti; arsip yang lengkap dicek hash, namespace NameNode yang sudah ada tidak diformat ulang.

Setelah `install.ready` tersedia:

```bash
bash ~/lab/start.sh
source ~/lab/env.sh
beeline -u "$HIVE_JDBC_URL" -n hadoop -e 'SELECT 1;'
```

Di PowerShell lain, salin materi ke VM:

```powershell
python native/environment/manage_vm.py sync
```

Lanjut di terminal VM:

```bash
cd ~/HadoopEcosystem
bash native/demo/00_check.sh
```

## Halaman untuk presentasi dari browser Windows

| Halaman | Alamat |
|---|---|
| NameNode HDFS | http://localhost:9870 |
| ResourceManager YARN | http://localhost:8088 |
| Riwayat MapReduce | http://localhost:19888/jobhistory |

Forwarding NAT dibatasi ke 127.0.0.1 pada host; tidak perlu membuka akses jaringan kampus. Port 2222 dipakai SSH. JDBC Hive digunakan dari terminal VM di localhost:10000. Link detail yang mengarah ke hostname/port dinamis guest dapat tidak dibuka dari Windows; tampilkan status dan log aplikasi dengan CLI di VM. Membaca isi file HDFS dilakukan dengan `hdfs dfs -cat`.

SSH key khusus lab ada di `native/environment/local/`, yang diabaikan Git. `known_hosts` khusus VM menyimpan identitas pada koneksi pertama. Jangan bagikan direktori ini atau menonaktifkan pemeriksaan host key saat ada perubahan identitas yang belum dijelaskan.

## Memulai sesi berikutnya dan mematikan dengan normal

Layanan lab dimulai manual pada setiap boot sehingga penggunaan RAM dapat dikendalikan:

```bash
bash ~/lab/start.sh
cd ~/HadoopEcosystem
bash native/demo/00_check.sh
```

Setelah selesai:

```bash
bash ~/lab/stop.sh
sudo shutdown -h now
```

Atau kirim tombol daya ACPI dari PowerShell:

```powershell
python native/environment/manage_vm.py stop
```

Jangan memakai `hdfs namenode -format` untuk mengulang demo. Buat sesi HDFS baru dengan `01_storage.sh` agar hasil sebelumnya tersimpan.

## Rujukan versi dan konfigurasi

- [Apache Hadoop: single node 3.3.6](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/SingleCluster.html).
- [Apache Hive: instalasi Hive 4 dan Hadoop 3.3.6](https://hive.apache.org/docs/latest/admin/manual-installation/).
- [Apache Hive: engine dan deprecation](https://hive.apache.org/docs/latest/).
- [Apache Pig: rilis 0.18 mendukung Hadoop 3](https://pig.apache.org/releases.html).
- [Ubuntu: cloud image Jammy dan checksum](https://cloud-images.ubuntu.com/jammy/current/).
