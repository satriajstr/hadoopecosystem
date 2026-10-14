#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command mapred
require_hdfs
load_demo_session
if hdfs dfs -test -e "$HDFS_BASE/immunization-output"; then
  printf 'Output sudah ada; buat sesi baru dengan 01_storage.sh.\n' >&2
  exit 1
fi
mapred streaming \
  -D mapreduce.framework.name=yarn \
  -D mapreduce.job.name=Modul4_ImmunizationMean \
  -D mapreduce.job.reduces=1 \
  -files code/immunization_mapper.py,code/immunization_reducer.py \
  -input "$HDFS_BASE/analytics" \
  -output "$HDFS_BASE/immunization-output" \
  -mapper 'python3 immunization_mapper.py' \
  -reducer 'python3 immunization_reducer.py' 2>&1 | tee "$RUN_DIR/immunization-job.log"
hdfs dfs -cat "$HDFS_BASE/immunization-output/part-*" | tee "$RUN_DIR/immunization-result.tsv"
