#!/usr/bin/env bash
# Jalankan dari root proyek di Linux/VM yang Hadoop dan HDFS/YARN-nya aktif.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${HADOOP_STREAMING_JAR:?Isi path absolut ke hadoop-streaming-*.jar}"
command -v hadoop >/dev/null
command -v hdfs >/dev/null
command -v python3 >/dev/null

# Namespace baru per eksekusi: output MapReduce wajib belum ada.
HDFS_BASE="/user/$(id -un)/modul4-$(date +%Y%m%d-%H%M%S)-$$"
hdfs dfs -mkdir -p "$HDFS_BASE/input" "$HDFS_BASE/students" "$HDFS_BASE/vaccinations"
hdfs dfs -put data/sample.txt "$HDFS_BASE/input/"
hdfs dfs -put data/students.csv "$HDFS_BASE/students/"
# CSV imunisasi memiliki header; hilangkan sebelum unggah.
tail -n +2 data/vaccinations.csv | hdfs dfs -put - "$HDFS_BASE/vaccinations/data.csv"

hadoop jar "$HADOOP_STREAMING_JAR" \
  -D mapreduce.framework.name=yarn \
  -D mapreduce.job.reduces=1 \
  -files code/mapper.py,code/reducer.py \
  -input "$HDFS_BASE/input" \
  -output "$HDFS_BASE/wordcount" \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py"

hdfs dfs -cat "$HDFS_BASE/wordcount/part-*"
printf '\nHDFS_BASE=%s\n' "$HDFS_BASE"
printf 'Salin nilai ini untuk --hivevar hdfs_base dan parameter Pig.\n'
