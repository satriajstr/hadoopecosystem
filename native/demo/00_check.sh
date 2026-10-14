#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

for tool in hadoop hdfs yarn mapred beeline python3; do
  require_command "$tool"
done
hadoop version
python3 --version
require_hdfs
hdfs dfs -ls /
hdfs dfsadmin -report
yarn node -list

[[ -f data/real/immunization_coverage_long.tsv ]] || {
  printf 'Dataset TSV belum tersedia. Siapkan dengan code/prepare_real_dataset.py.\n' >&2
  exit 1
}
: "${HIVE_JDBC_URL:?Isi URL JDBC HiveServer2 sesuai lingkungan lab}"
beeline -u "$HIVE_JDBC_URL" -n "${HIVE_USER:-$(id -un)}" -e 'SELECT 1;'
printf '\nPemeriksaan HDFS, YARN, dan koneksi Beeline berhasil. Periksa jumlah node hidup di atas.\n'
printf 'Job Word Count dan query data tetap harus diuji pada langkah berikut.\n'
printf 'Pig opsional: '
if command -v pig >/dev/null 2>&1; then command -v pig; else printf 'belum tersedia\n'; fi
