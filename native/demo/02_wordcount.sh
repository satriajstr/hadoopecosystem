#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command mapred
require_command yarn
require_hdfs
load_demo_session

if hdfs dfs -test -e "$HDFS_BASE/wordcount-output"; then
  printf 'Output sudah ada. Buat sesi baru dengan 01_storage.sh untuk mengulang job.\n' >&2
  exit 1
fi

mapred streaming \
  -D mapreduce.framework.name=yarn \
  -D "mapreduce.job.name=Modul4 WordCount ${HDFS_BASE##*/}" \
  -D mapreduce.job.reduces=1 \
  -files code/mapper.py,code/reducer.py \
  -input "$HDFS_BASE/wordcount-input" \
  -output "$HDFS_BASE/wordcount-output" \
  -mapper "python3 mapper.py" \
  -reducer "python3 reducer.py" 2>&1 | tee "$RUN_DIR/wordcount-job.log"

hdfs dfs -cat "$HDFS_BASE/wordcount-output/part-*" | tee "$RUN_DIR/wordcount-result.tsv"
APP_ID="$(grep -Eo 'application_[0-9]+_[0-9]+' "$RUN_DIR/wordcount-job.log" | tail -n 1)"
if [[ -n "$APP_ID" ]]; then
  yarn application -status "$APP_ID" 2>&1 | tee "$RUN_DIR/yarn-status.log"
  printf '%s\n' "$APP_ID" > "$RUN_DIR/application-id.txt"
fi
printf '\nSalin application_... dari log untuk yarn application -status ID_AKTUAL.\n'
printf 'Job kecil dapat selesai cepat; status FINISHED/SUCCEEDED adalah hasil yang diharapkan.\n'
