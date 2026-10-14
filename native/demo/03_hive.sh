#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
require_command beeline
require_hdfs
load_demo_session
: "${HIVE_JDBC_URL:?Isi URL JDBC HiveServer2 sesuai lingkungan lab}"

beeline -u "$HIVE_JDBC_URL" -n "${HIVE_USER:-$(id -un)}" \
  --hivevar "hdfs_real=$HDFS_BASE/analytics" \
  -i native/real_setup_hive.hql \
  -f native/demo/hive_walkthrough.sql 2>&1 | tee "$RUN_DIR/hive-session.log"

printf '\nPeriksa hasil tiap query pada log Hive; log tersimpan di %s\n' "$RUN_DIR"
