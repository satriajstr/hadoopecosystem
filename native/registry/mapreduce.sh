#!/usr/bin/env bash
# Submit registry coverage to a configured Hadoop/YARN cluster.
set -euo pipefail
RUN_ID="$(date +%Y%m%d-%H%M%S)-$$"
HDFS_BASE="/user/$(id -un)/modul4-registry-$RUN_ID"
hdfs dfs -mkdir -p "$HDFS_BASE/children"
hdfs dfs -put data/dummy/children.tsv "$HDFS_BASE/children/children.tsv"
mapred streaming \
  -D mapreduce.framework.name=yarn \
  -D mapreduce.job.name=Modul4_DummyRegistryCoverage \
  -D mapreduce.job.reduces=1 \
  -files code/registry_mapper.py,code/registry_reducer.py \
  -input "$HDFS_BASE/children" \
  -output "$HDFS_BASE/coverage" \
  -mapper 'python3 registry_mapper.py' \
  -reducer 'python3 registry_reducer.py'
hdfs dfs -cat "$HDFS_BASE/coverage/part-*"
printf '\nHDFS_BASE=%s\n' "$HDFS_BASE"
