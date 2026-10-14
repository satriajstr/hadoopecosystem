#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command pig
require_hdfs
load_demo_session

if hdfs dfs -test -e "$HDFS_BASE/pig-output"; then
  printf 'Output Pig sudah ada. Gunakan sesi baru untuk mengulang.\n' >&2
  exit 1
fi

pig -x mapreduce \
  -param "INPUT=$HDFS_BASE/analytics/coverage.tsv" \
  -param "OUTPUT=$HDFS_BASE/pig-output" \
  native/demo/real_filter_group.pig 2>&1 | tee "$RUN_DIR/pig-session.log"

hdfs dfs -cat "$HDFS_BASE/pig-output/by-country-year/part-*" | tee "$RUN_DIR/pig-by-country-year.tsv"
printf '\nSetiap kelompok negara/tahun berisi dua observasi indikator, bukan dua anak.\n'
