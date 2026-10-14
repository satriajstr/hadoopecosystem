#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_hdfs
[[ -s data/sample.txt && -s data/real/immunization_coverage_long.tsv ]]

SESSION_ID="$(date +%Y%m%d-%H%M%S)-$$"
RUN_DIR="$NATIVE_OUTPUT/runs/$SESSION_ID"
HDFS_BASE="/user/$(id -un)/modul4-demo-$SESSION_ID"
mkdir -p "$RUN_DIR"

# Dua file input berasal dari tiga baris teks yang sama; tidak menambah record.
head -n 2 data/sample.txt > "$RUN_DIR/sample-a.txt"
tail -n +3 data/sample.txt > "$RUN_DIR/sample-b.txt"

hdfs dfs -mkdir -p "$HDFS_BASE/wordcount-input" "$HDFS_BASE/analytics"
hdfs dfs -put "$RUN_DIR/sample-a.txt" "$RUN_DIR/sample-b.txt" "$HDFS_BASE/wordcount-input/"
hdfs dfs -put data/real/immunization_coverage_long.tsv "$HDFS_BASE/analytics/coverage.tsv"

{
  printf 'HDFS_BASE=%q\n' "$HDFS_BASE"
  printf 'RUN_DIR=%q\n' "$RUN_DIR"
} > "$NATIVE_OUTPUT/latest.env"

hdfs dfs -ls -R "$HDFS_BASE"
hdfs dfs -du -h "$HDFS_BASE"
hdfs dfs -cat "$HDFS_BASE/wordcount-input/sample-a.txt"
hdfs dfs -head "$HDFS_BASE/analytics/coverage.tsv"
hdfs fsck "$HDFS_BASE" -files -blocks -locations | tee "$RUN_DIR/hdfs-fsck.log"
printf '\nSesi tersimpan di %s/latest.env\n' "$NATIVE_OUTPUT"
printf 'Jumlah DataNode dan lokasi blok adalah bukti topologi aktual, bukan asumsi.\n'
