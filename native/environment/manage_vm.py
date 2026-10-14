"""Prepare/run the project-owned VirtualBox lab. Windows host, Python stdlib.

All VM state, downloads, keys, logs and seed ISO remain inside the project.
prepare never starts a VM; start enforces host RAM/disk headroom.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'native/environment/local'
OUT = ROOT / 'output/environment'
NAME = 'HadoopEcosystem-Modul4'
VBOX = Path(r'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe')
SSH = Path(r'C:\Windows\System32\OpenSSH\ssh.exe')
KEYGEN = SSH.with_name('ssh-keygen.exe')
IMAGE_NAME = 'jammy-server-cloudimg-amd64.vmdk'
IMAGE_BASE = 'https://cloud-images.ubuntu.com/jammy/current/'


def call(*args, capture=False):
    return subprocess.run([str(x) for x in args], cwd=ROOT, check=True,
                          text=True, capture_output=capture)


def vbox(*args, capture=False):
    return call(VBOX, *args, capture=capture)


def vm_info():
    result = subprocess.run([str(VBOX), 'showvminfo', NAME, '--machinereadable'],
                            capture_output=True, text=True)
    if result.returncode:
        return {}
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def require_owned_vm():
    info = vm_info()
    if not info:
        raise RuntimeError('Project VM is not registered; run prepare first')
    config = Path(info['CfgFile'].strip('"')).resolve()
    if not config.is_relative_to(LOCAL.resolve()):
        raise RuntimeError('VM name belongs to a different directory; refusing to operate it')
    return info


def resources():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (x, ctypes.c_ulonglong) for x in ('total', 'available', 'total_page',
                'available_page', 'total_virtual', 'available_virtual', 'extended')]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError('Cannot check available host RAM')
    return {'ram_free_gib': round(memory.available / 2**30, 2),
            'disk_free_gib': round(shutil.disk_usage(ROOT).free / 2**30, 2)}


def download(url, target):
    partial = target.with_suffix(target.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=90) as response, partial.open('wb') as f:
        total = int(response.headers.get('Content-Length', 0))
        count, last = 0, 0
        while chunk := response.read(1024 * 1024):
            f.write(chunk)
            count += len(chunk)
            if time.monotonic() - last > 10:
                print(f'Download {target.name}: {count // 2**20} / {total // 2**20} MiB', flush=True)
                last = time.monotonic()
    partial.replace(target)


def sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def prepare():
    if not VBOX.exists():
        raise RuntimeError('VirtualBox CLI is not installed')
    if vm_info():
        info = require_owned_vm()
        if info.get('VMState') != '"poweroff"':
            raise RuntimeError('Stop the project VM before changing its cloud-init seed')
    if resources()['disk_free_gib'] < 12:
        raise RuntimeError('Preparation needs at least 12 GiB free on the project drive')
    LOCAL.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    image = LOCAL / IMAGE_NAME
    sums = LOCAL / 'SHA256SUMS'
    provenance = LOCAL / 'image-provenance.json'
    if provenance.exists() and image.exists():
        expected = json.loads(provenance.read_text())['sha256']
    else:
        download(IMAGE_BASE + 'SHA256SUMS', sums)
        matches = [line.split()[0] for line in sums.read_text().splitlines()
                   if line.split()[-1].lstrip('*') == IMAGE_NAME]
        if len(matches) != 1:
            raise RuntimeError('Ubuntu checksum manifest has no unique VMDK match')
        expected = matches[0]
        if not image.exists():
            download(IMAGE_BASE + IMAGE_NAME, image)
    actual = sha256(image)
    if actual != expected:
        raise RuntimeError('Ubuntu image checksum mismatch; VM creation stopped')
    provenance.write_text(json.dumps({'url': IMAGE_BASE + IMAGE_NAME,
        'sha256': actual, 'verified_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, indent=2))
    key = LOCAL / 'id_ed25519'
    if not key.exists():
        call(KEYGEN, '-t', 'ed25519', '-N', '', '-C', 'modul4-local-vm', '-f', key)
    public = key.with_suffix('.pub').read_text().strip()
    sys.path.insert(0, str(ROOT / 'tmp/vm-tools'))
    import pycdlib
    installer = (ROOT / 'native/environment/install_guest.sh').read_text()
    cloud = {'hostname': 'hadoop-demo', 'manage_etc_hosts': True,
        'users': [{'name': 'hadoop', 'groups': ['sudo'], 'shell': '/bin/bash',
                   'sudo': 'ALL=(ALL) NOPASSWD:ALL', 'lock_passwd': True,
                   'ssh_authorized_keys': [public]}],
        'ssh_pwauth': False, 'disable_root': True,
        'package_update': True,
        'packages': ['openjdk-8-jdk-headless', 'python3', 'curl', 'openssh-server', 'gnupg'],
        'write_files': [{'path': '/home/hadoop/install_guest.sh', 'permissions': '0755',
                         'content': installer}],
        'runcmd': [['chown', 'hadoop:hadoop', '/home/hadoop/install_guest.sh'],
                   ['su', '-', 'hadoop', '-c', 'bash /home/hadoop/install_guest.sh > /home/hadoop/install.log 2>&1']]}
    userdata = ('#cloud-config\n' + json.dumps(cloud)).encode()
    metadata = json.dumps({'instance-id': 'modul4-ubuntu-20261008', 'local-hostname': 'hadoop-demo'}).encode()
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, rock_ridge='1.09', vol_ident='cidata')
    for iso_name, name, content in [('USER_DAT.;1', 'user-data', userdata), ('META_DAT.;1', 'meta-data', metadata)]:
        iso.add_fp(io.BytesIO(content), len(content), iso_path='/' + iso_name,
                   rr_name=name, joliet_path='/' + name)
    iso.write(str(LOCAL / 'seed.iso'))
    iso.close()
    registered = vbox('list', 'vms', capture=True).stdout
    if f'"{NAME}"' not in registered:
        disk = LOCAL / 'hadoop-lab.vdi'
        if not disk.exists():
            vbox('clonemedium', 'disk', image, disk, '--format', 'VDI')
            vbox('modifymedium', 'disk', disk, '--resize', '32768')
        vbox('createvm', '--name', NAME, '--ostype', 'Ubuntu_64', '--basefolder', LOCAL / 'vm', '--register')
        vbox('modifyvm', NAME, '--memory', '6144', '--cpus', '4', '--vram', '16',
             '--nic1', 'nat', '--nic-type1', 'virtio', '--audio-enabled', 'off',
             '--graphicscontroller', 'vmsvga', '--boot1', 'disk', '--boot2', 'none')
        for label, hostport, guestport in [('ssh', 2222, 22), ('hdfs', 9870, 9870), ('yarn', 8088, 8088), ('history', 19888, 19888)]:
            vbox('modifyvm', NAME, '--nat-pf1', f'{label},tcp,127.0.0.1,{hostport},,{guestport}')
        vbox('storagectl', NAME, '--name', 'SATA', '--add', 'sata', '--controller', 'IntelAhci')
        vbox('storageattach', NAME, '--storagectl', 'SATA', '--port', '0', '--device', '0', '--type', 'hdd', '--medium', disk)
        vbox('storageattach', NAME, '--storagectl', 'SATA', '--port', '1', '--device', '0', '--type', 'dvddrive', '--medium', LOCAL / 'seed.iso')
    print('PREPARED: image hash verified, seed created, project VM registered. VM has not been started.')
    status()


def start():
    require_owned_vm()
    state = resources()
    print(json.dumps(state), flush=True)
    if state['ram_free_gib'] < 8:
        raise RuntimeError('VM needs 8 GiB free host RAM (6 GiB guest plus headroom). Close unused apps first.')
    minimum_disk = 4 if (LOCAL / 'first-start.json').exists() else 10
    if state['disk_free_gib'] < minimum_disk:
        raise RuntimeError(f'VM start needs at least {minimum_disk} GiB free project disk')
    vbox('startvm', NAME, '--type', 'headless')
    if not (LOCAL / 'first-start.json').exists():
        (LOCAL / 'first-start.json').write_text(json.dumps({'started_utc':
            time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'installation_verified': False}))


def ssh_args():
    return [SSH, '-i', LOCAL / 'id_ed25519', '-p', '2222',
            '-o', f'UserKnownHostsFile={LOCAL / "known_hosts"}',
            '-o', 'StrictHostKeyChecking=accept-new', '-o', 'IdentitiesOnly=yes', 'hadoop@127.0.0.1']


def sync():
    # Transfer only reviewable project source/data. Never recursively copy keys or VM disks.
    import tarfile
    require_owned_vm()
    bundle = OUT / 'project.tar.gz'
    with tarfile.open(bundle, 'w:gz') as tar:
        for path in [ROOT/'code', ROOT/'data', ROOT/'native/demo',
                     ROOT/'native/real_setup_hive.hql', ROOT/'native/real_immunization.sql',
                     ROOT/'DEMO_MANUAL_HADOOP.md']:
            tar.add(path, arcname=str(path.relative_to(ROOT)).replace('\\', '/'),
                    filter=lambda member: None if '__pycache__' in member.name else member)
    with bundle.open('rb') as source:
        subprocess.run([str(x) for x in ssh_args()] + ['mkdir -p ~/HadoopEcosystem && tar -xzf - -C ~/HadoopEcosystem'],
                       stdin=source, cwd=ROOT, check=True)
    print('SYNCED: code, data and demo files to ~/HadoopEcosystem in project VM')


def status():
    OUT.mkdir(parents=True, exist_ok=True)
    state = resources()
    result = subprocess.run([str(VBOX), 'showvminfo', NAME, '--machinereadable'],
                            capture_output=True, text=True)
    state['registered'] = result.returncode == 0
    state['vm'] = NAME
    state['vm_state'] = next((line.split('=',1)[1].strip('"') for line in result.stdout.splitlines()
                             if line.startswith('VMState=')), 'not-created')
    state['native_hadoop_validation'] = 'NOT RUN; see native demo logs after guest installation'
    (OUT / 'host-status.json').write_text(json.dumps(state, indent=2))
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'start', 'status', 'sync', 'ssh', 'stop'])
    args = parser.parse_args()
    try:
        if args.action == 'ssh':
            require_owned_vm()
            call(*ssh_args())
        elif args.action == 'stop':
            require_owned_vm()
            vbox('controlvm', NAME, 'acpipowerbutton')
        else:
            globals()[args.action]()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
