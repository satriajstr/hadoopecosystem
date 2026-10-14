"""Small byte-block model: metadata, replicas, checksums, and node recovery."""
import copy
import hashlib
from pathlib import Path
from prepare_dummy_dataset import save_json

BLOCK_SIZE = 16 * 1024  # Teaching size so this small registry has several blocks.
NODES = ('DN1', 'DN2', 'DN3')


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def write_blocks(source, names, root, block_size=BLOCK_SIZE, replication=2):
    if block_size <= 0 or not 1 <= replication <= len(NODES):
        raise ValueError('Invalid block size or replication factor')
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'block_size_bytes': block_size, 'replication': replication,
                'nodes': {node: 'ONLINE' for node in NODES}, 'files': {}}
    ordinal = 0
    for name in names:
        data = (Path(source)/name).read_bytes()
        blocks = []
        for offset in range(0, len(data), block_size):
            part = data[offset:offset+block_size]
            block_id = f'blk_{ordinal:05d}'
            replicas = [NODES[(ordinal+i) % len(NODES)] for i in range(replication)]
            for node in replicas:
                folder = root/'datanodes'/node
                folder.mkdir(parents=True, exist_ok=True)
                (folder/block_id).write_bytes(part)
            blocks.append({'id': block_id, 'bytes': len(part),
                           'sha256': checksum(part), 'replicas': replicas})
            ordinal += 1
        manifest['files'][name] = {'bytes': len(data), 'sha256': checksum(data), 'blocks': blocks}
    save_json(root/'namenode.json', manifest)
    return manifest


def read_block(root, manifest, block):
    for node in block['replicas']:
        path = Path(root)/'datanodes'/node/block['id']
        if manifest['nodes'][node] != 'ONLINE' or not path.is_file():
            continue
        data = path.read_bytes()
        if len(data) == block['bytes'] and checksum(data) == block['sha256']:
            return data, node
    raise ValueError('No healthy replica for '+block['id'])


def read_file(root, manifest, name):
    # The client gets locations from metadata, then reads bytes from DataNodes.
    chunks, trace = [], []
    for block in manifest['files'][name]['blocks']:
        data, node = read_block(root, manifest, block)
        chunks.append(data)
        trace.append({'block': block['id'], 'node': node})
    result = b''.join(chunks)
    expected = manifest['files'][name]
    if len(result) != expected['bytes'] or checksum(result) != expected['sha256']:
        raise ValueError('Reconstructed file differs from metadata: '+name)
    return result, trace


def repair_replicas(root, manifest):
    repairs = []
    for info in manifest['files'].values():
        for block in info['blocks']:
            data, source = read_block(root, manifest, block)
            healthy = []
            for node in block['replicas']:
                path = Path(root)/'datanodes'/node/block['id']
                if manifest['nodes'][node] == 'ONLINE' and path.is_file() and checksum(path.read_bytes()) == block['sha256']:
                    healthy.append(node)
            for target in NODES:
                if len(healthy) >= manifest['replication']:
                    break
                if target in healthy or manifest['nodes'][target] != 'ONLINE':
                    continue
                folder = Path(root)/'datanodes'/target
                folder.mkdir(parents=True, exist_ok=True)
                (folder/block['id']).write_bytes(data)
                healthy.append(target)
                repairs.append({'block': block['id'], 'source': source, 'target': target})
            block['replicas'] = healthy
    save_json(Path(root)/'namenode.json', manifest)
    return repairs


def demonstrate_storage(source, names, root, destination):
    root, destination = Path(root), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = write_blocks(source, names, root)
    initial = copy.deepcopy(manifest)
    before = {}
    for name in names:
        data, before[name] = read_file(root, manifest, name)
        (destination/name).write_bytes(data)
    # A failed heartbeat excludes DN1; its old files are not usable replicas.
    manifest['nodes']['DN1'] = 'OFFLINE'
    after = {}
    for name in names:
        data, after[name] = read_file(root, manifest, name)
        if data != (destination/name).read_bytes():
            raise ValueError('Read after node failure differs from the initial read')
    repairs = repair_replicas(root, manifest)
    for name in names:
        read_file(root, manifest, name)
    evidence = {'initial': initial, 'after_failure': copy.deepcopy(manifest),
                'read_before_failure': before, 'read_after_failure': after,
                'failed_node': 'DN1', 'repairs': repairs,
                'all_files_match_after_failure': True,
                'replication_restored': all(len(b['replicas']) == manifest['replication']
                    for f in manifest['files'].values() for b in f['blocks'])}
    save_json(root/'results.json', evidence)
    return evidence


def verify_storage(root, destination):
    import json
    root = Path(root)
    manifest = json.loads((root/'namenode.json').read_text(encoding='utf-8'))
    for name in manifest['files']:
        data, _ = read_file(root, manifest, name)
        if data != (Path(destination)/name).read_bytes():
            raise ValueError('Storage snapshot differs from block replicas: '+name)


def print_storage(evidence,detail=False):
    initial = evidence['initial']
    if not detail:
        blocks = sum(len(info['blocks']) for info in initial['files'].values())
        print('Blok:',blocks,'| ukuran:',initial['block_size_bytes']//1024,'KiB | replika:',initial['replication'])
        print('DN1 OFFLINE | file terbaca dari DN2/DN3 | hash cocok')
        print('Replika pengganti:',len(evidence['repairs']),'blok | pulih:',
              'ya' if evidence['replication_restored'] else 'belum')
        return
    print('Blok = potongan file. Replika = salinan potongan itu.')
    print('NameNode mencatat lokasi; DN1, DN2, DN3 adalah tempat penyimpanan (DataNode).')
    print('Ukuran potongan:', initial['block_size_bytes']//1024, 'KiB | salinan per potongan:', initial['replication'])
    for name, info in initial['files'].items():
        print(name, '->', len(info['blocks']), 'blok |', info['bytes'], 'byte')
    for block in initial['files']['children.tsv']['blocks'][:3]:
        print(' ', block['id'], '->', ', '.join(block['replicas']))
    print('DN1 OFFLINE = satu tempat penyimpanan dibuat gagal dalam latihan.')
    print('File tetap terbaca dari salinan di DN2/DN3. Pemeriksaan isi (hash): cocok.')
    print('Salinan pengganti dibuat untuk', len(evidence['repairs']), 'blok.')
    print('Setiap blok kembali memiliki dua salinan:', 'ya' if evidence['replication_restored'] else 'belum')
