#!/usr/bin/env bash
# Runs only in the newly created project VM as user hadoop, via cloud-init.
set -euo pipefail
[[ $(id -un) == hadoop && $(hostname) == hadoop-demo ]] || {
  echo 'This installer is restricted to the project lab VM.' >&2; exit 1;
}
LAB="$HOME/lab"
mkdir -p "$LAB"/{downloads,software,state,logs,run}
exec > >(tee -a "$LAB/logs/install.log") 2>&1
trap 'echo "INSTALL FAILED at line $LINENO"; touch "$LAB/state/install.failed"' ERR

fetch_extract() {
  local url="$1" archive="$2" folder="$3" verification="$4"
  if [[ ! -f "$LAB/downloads/$archive" ]]; then
    curl --fail --location --retry 3 --connect-timeout 30 "$url/$archive" -o "$LAB/downloads/$archive.partial"
    mv "$LAB/downloads/$archive.partial" "$LAB/downloads/$archive"
  fi
  if [[ "$verification" == pgp ]]; then
    curl --fail --location --retry 3 "$url/$archive.asc" -o "$LAB/downloads/$archive.asc"
    curl --fail --location --retry 3 https://downloads.apache.org/pig/KEYS -o "$LAB/downloads/pig-KEYS"
    mkdir -p "$LAB/pgp"
    chmod 700 "$LAB/pgp"
    gpg --homedir "$LAB/pgp" --batch --import "$LAB/downloads/pig-KEYS"
    gpg --homedir "$LAB/pgp" --batch --verify "$LAB/downloads/$archive.asc" "$LAB/downloads/$archive"
  else
    curl --fail --location --retry 3 "$url/$archive.$verification" -o "$LAB/downloads/$archive.$verification"
    python3 - "$LAB/downloads/$archive" "$LAB/downloads/$archive.$verification" "$verification" <<'PY'
import hashlib, pathlib, re, sys
path, manifest = map(pathlib.Path, sys.argv[1:3])
algorithm = sys.argv[3]
length = {'sha256': 64, 'sha512': 128}[algorithm]
text = manifest.read_text()
tokens = re.findall(r'(?<![a-fA-F0-9])[a-fA-F0-9]{'+str(length)+r'}(?![a-fA-F0-9])', text)
if not tokens:  # Some Apache manifests wrap the hex digest into 8-character groups.
    groups = re.findall(r'(?<![a-fA-F0-9])[a-fA-F0-9]{8}(?![a-fA-F0-9])', text)
    if len(groups) == length // 8:
        tokens = [''.join(groups)]
if len(tokens) != 1:
    raise SystemExit('Cannot identify a unique checksum in ' + str(manifest))
h = hashlib.new(algorithm)
with path.open('rb') as f:
    for chunk in iter(lambda: f.read(1024*1024), b''):
        h.update(chunk)
actual = h.hexdigest()
if actual.lower() != tokens[0].lower():
    raise SystemExit('Checksum mismatch: ' + str(path))
print(algorithm.upper() + ' VERIFIED:', path.name, actual)
PY
  fi
  if [[ ! -d "$LAB/software/$folder" ]]; then
    tar -xzf "$LAB/downloads/$archive" -C "$LAB/software"
  fi
}

fetch_extract https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6 hadoop-3.3.6.tar.gz hadoop-3.3.6 sha512
fetch_extract https://archive.apache.org/dist/hive/hive-4.0.1 apache-hive-4.0.1-bin.tar.gz apache-hive-4.0.1-bin sha256

cat > "$LAB/env.sh" <<'ENV'
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export LAB="$HOME/lab"
export HADOOP_HOME="$LAB/software/hadoop-3.3.6"
export HADOOP_COMMON_HOME="$HADOOP_HOME"
export HADOOP_HDFS_HOME="$HADOOP_HOME"
export HADOOP_YARN_HOME="$HADOOP_HOME"
export HADOOP_MAPRED_HOME="$HADOOP_HOME"
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
export HIVE_HOME="$LAB/software/apache-hive-4.0.1-bin"
export PIG_HOME="$LAB/software/pig-0.18.0"
export HADOOP_LOG_DIR="$LAB/logs/hadoop"
export HADOOP_PID_DIR="$LAB/run"
export HADOOP_HEAPSIZE_MAX=384
export HADOOP_CLIENT_OPTS='-Xmx512m'
export HIVE_SERVER2_HEAPSIZE=1024
export HADOOP_HEAPSIZE=512
export HIVE_JDBC_URL='jdbc:hive2://localhost:10000/default'
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HIVE_HOME/bin:$PIG_HOME/bin:$PATH"
ENV
source "$LAB/env.sh"
if ! grep -q 'lab/env.sh' "$HOME/.profile"; then
  printf '\nsource "$HOME/lab/env.sh"\n' >> "$HOME/.profile"
fi
mkdir -p "$LAB"/{hdfs/name,hdfs/data,tmp,hive/warehouse,logs/hadoop,metastore}
printf '\nexport JAVA_HOME=%s\nexport HADOOP_HEAPSIZE_MAX=384\n' "$JAVA_HOME" >> "$HADOOP_CONF_DIR/hadoop-env.sh"

python3 - <<'PY'
import os, pathlib, xml.etree.ElementTree as E
lab = os.environ['LAB']
def write(path, values):
    root = E.Element('configuration')
    for name, value in values.items():
        prop = E.SubElement(root, 'property')
        E.SubElement(prop, 'name').text = name
        E.SubElement(prop, 'value').text = str(value)
    E.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
conf = pathlib.Path(os.environ['HADOOP_CONF_DIR'])
write(conf/'core-site.xml', {'fs.defaultFS': 'hdfs://localhost:9000', 'hadoop.tmp.dir': lab+'/tmp'})
write(conf/'hdfs-site.xml', {'dfs.replication': 1, 'dfs.namenode.name.dir': 'file:'+lab+'/hdfs/name',
    'dfs.datanode.data.dir': 'file:'+lab+'/hdfs/data', 'dfs.namenode.http-address': '0.0.0.0:9870',
    'dfs.datanode.http.address': '0.0.0.0:9864'})
write(conf/'mapred-site.xml', {'mapreduce.framework.name': 'yarn',
    'mapreduce.application.classpath': '$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/*:$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/lib/*',
    'yarn.app.mapreduce.am.resource.mb': 512, 'yarn.app.mapreduce.am.command-opts': '-Xmx384m',
    'mapreduce.map.memory.mb': 512, 'mapreduce.map.java.opts': '-Xmx384m',
    'mapreduce.reduce.memory.mb': 512, 'mapreduce.reduce.java.opts': '-Xmx384m',
    'mapreduce.jobhistory.address': 'localhost:10020', 'mapreduce.jobhistory.webapp.address': '0.0.0.0:19888'})
write(conf/'yarn-site.xml', {'yarn.resourcemanager.hostname': 'localhost',
    'yarn.resourcemanager.webapp.address': '0.0.0.0:8088',
    'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
    'yarn.nodemanager.env-whitelist': 'JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME,PATH,LANG,TZ',
    'yarn.nodemanager.resource.memory-mb': 3072, 'yarn.nodemanager.resource.cpu-vcores': 4,
    'yarn.scheduler.minimum-allocation-mb': 256, 'yarn.scheduler.maximum-allocation-mb': 3072,
    'yarn.log-aggregation-enable': 'true', 'yarn.nodemanager.remote-app-log-dir': '/tmp/yarn-logs',
    'yarn.nodemanager.vmem-check-enabled': 'false',
    'yarn.nodemanager.local-dirs': lab+'/yarn/local', 'yarn.nodemanager.log-dirs': lab+'/yarn/logs'})
write(pathlib.Path(os.environ['HIVE_HOME'])/'conf/hive-site.xml', {
    'javax.jdo.option.ConnectionURL': 'jdbc:derby:;databaseName='+lab+'/metastore/db;create=true',
    'javax.jdo.option.ConnectionDriverName': 'org.apache.derby.jdbc.EmbeddedDriver',
    'javax.jdo.option.ConnectionUserName': 'APP', 'javax.jdo.option.ConnectionPassword': 'mine',
    'hive.metastore.schema.verification': 'true', 'datanucleus.schema.autoCreateAll': 'false',
    'hive.metastore.warehouse.dir': '/user/hive/warehouse',
    'hive.server2.thrift.bind.host': '0.0.0.0', 'hive.server2.thrift.port': 10000,
    'hive.server2.authentication': 'NONE', 'hive.server2.enable.doAs': 'false',
    'hive.execution.engine': 'mr', 'hive.fetch.task.conversion': 'none',
    'hive.server2.tez.initialize.default.sessions': 'false',
    'hive.support.concurrency': 'false', 'hive.txn.manager': 'org.apache.hadoop.hive.ql.lockmgr.DummyTxnManager',
    'hive.stats.autogather': 'false', 'hive.exec.scratchdir': '/tmp/hive',
    'hive.exec.local.scratchdir': lab+'/hive/scratch'})
PY

# Initialize only a fresh namespace. Never reformat existing state.
if [[ ! -f "$LAB/hdfs/name/current/VERSION" ]]; then
  [[ -z $(ls -A "$LAB/hdfs/name") ]] || { echo 'Unknown nonempty NameNode state; refusing format.' >&2; exit 1; }
  hdfs namenode -format -nonInteractive
fi
if [[ ! -f "$LAB/state/schema.ready" ]]; then
  schematool -dbType derby -initSchema
  touch "$LAB/state/schema.ready"
fi

cat > "$LAB/start.sh" <<'START'
#!/usr/bin/env bash
set -euo pipefail
source "$HOME/lab/env.sh"
running() { jps | awk '{print $2}' | grep -qx "$1"; }
running NameNode || hdfs --daemon start namenode
running DataNode || hdfs --daemon start datanode
running ResourceManager || yarn --daemon start resourcemanager
running NodeManager || yarn --daemon start nodemanager
running JobHistoryServer || mapred --daemon start historyserver
hdfs dfsadmin -safemode wait
hdfs dfs -mkdir -p /user/hadoop /user/hive/warehouse /tmp/hive /tmp/yarn-logs
hdfs dfs -chmod 1777 /tmp
if ! python3 -c 'import socket; socket.create_connection(("127.0.0.1",10000),2)' 2>/dev/null; then
  if [[ -f "$LAB/run/hiveserver2.pid" ]] && kill -0 "$(cat "$LAB/run/hiveserver2.pid")" 2>/dev/null; then
    echo 'HiveServer2 is starting; check lab/logs/hiveserver2.log.'
  else
    nohup hiveserver2 > "$LAB/logs/hiveserver2.log" 2>&1 < /dev/null &
    echo $! > "$LAB/run/hiveserver2.pid"
  fi
fi
jps
echo 'HiveServer2 can take a minute to initialize. Verify with Beeline, not only jps.'
START
cat > "$LAB/stop.sh" <<'STOP'
#!/usr/bin/env bash
set -euo pipefail
source "$HOME/lab/env.sh"
if [[ -f "$LAB/run/hiveserver2.pid" ]]; then
  pid="$(cat "$LAB/run/hiveserver2.pid")"
  if kill -0 "$pid" 2>/dev/null && [[ $(ps -p "$pid" -o args=) == *HiveServer2* ]]; then kill "$pid"; fi
fi
mapred --daemon stop historyserver
yarn --daemon stop nodemanager
yarn --daemon stop resourcemanager
hdfs --daemon stop datanode
hdfs --daemon stop namenode
STOP
chmod +x "$LAB/start.sh" "$LAB/stop.sh"
touch "$LAB/state/install.ready"
echo 'INSTALL READY: start services with bash ~/lab/start.sh; native jobs not yet verified.'
# Optional stage runs after the core lab is installed. A Pig download failure does
# not remove install.ready, so the 25-minute core demo can still be started.
fetch_extract https://downloads.apache.org/pig/pig-0.18.0 pig-0.18.0.tar.gz pig-0.18.0 pgp
touch "$LAB/state/pig.ready"
echo 'PIG READY: optional package installed; native Pig job not yet verified.'
