#!/usr/bin/env bash
# Helper sesi demo. Dipanggil oleh script per tahap; bukan launcher instalasi.
DEMO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NATIVE_OUTPUT="$DEMO_ROOT/output/native-demo"
cd "$DEMO_ROOT"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Perintah %s belum tersedia pada lingkungan ini.\n' "$1" >&2
    return 1
  }
}

require_hdfs() {
  require_command hdfs
  local configured_fs
  configured_fs="$(hdfs getconf -confKey fs.defaultFS)"
  case "$configured_fs" in
    hdfs://*) printf 'Filesystem Hadoop: %s\n' "$configured_fs" ;;
    *) printf 'fs.defaultFS=%s; demo ini membutuhkan HDFS, bukan filesystem lokal.\n' "$configured_fs" >&2; return 1 ;;
  esac
}

load_demo_session() {
  [[ -f "$NATIVE_OUTPUT/latest.env" ]] || {
    printf 'Jalankan 01_storage.sh dahulu untuk membuat sesi demo.\n' >&2
    return 1
  }
  # File ini hanya dibuat oleh 01_storage.sh dari nilai sesi lokal.
  source "$NATIVE_OUTPUT/latest.env"
  [[ -n "${HDFS_BASE:-}" && -d "${RUN_DIR:-}" ]] || return 1
  printf 'Sesi HDFS: %s\n' "$HDFS_BASE"
}
