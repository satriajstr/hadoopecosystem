"""Resource-budget model tied to actual Python task execution."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4


class YarnApplication:
    def __init__(self, node_count=3, cpu=1, memory_mb=1024):
        if node_count < 2 or cpu < 1 or memory_mb < 512:
            raise ValueError('The application needs an AM and task resources')
        self.nodes = {f'NM{i+1}': {'cpu': cpu, 'memory_mb': memory_mb,
                      'used_cpu': 0, 'used_memory_mb': 0} for i in range(node_count)}
        self.application_id = 'demo_app_'+uuid4().hex[:10]
        self.events, self.containers = [], {}
        self.state = 'NEW'
        self.started = perf_counter()
        self.record('ResourceManager', 'SUBMITTED', self.application_id)
        self.state = 'SUBMITTED'
        self.record('ResourceManager', 'ACCEPTED', 'ApplicationMaster requested')
        self.state = 'ACCEPTED'
        self.am = self.allocate('ApplicationMaster', 1, 256)
        if self.am is None:
            raise ValueError('Insufficient resources for ApplicationMaster')
        self.state = 'RUNNING'
        self.record('ApplicationMaster', 'RUNNING', self.application_id)

    def record(self, actor, event, detail):
        self.events.append({'sequence': len(self.events)+1, 'actor': actor,
            'event': event, 'detail': detail, 'elapsed_ms': round((perf_counter()-self.started)*1000, 3),
            'utc': datetime.now(timezone.utc).isoformat(),
            'resources': {node: dict(value) for node, value in self.nodes.items()}})

    def allocate(self, task, cpu=1, memory_mb=512):
        for node, resources in self.nodes.items():
            if resources['used_cpu']+cpu > resources['cpu'] or resources['used_memory_mb']+memory_mb > resources['memory_mb']:
                continue
            resources['used_cpu'] += cpu
            resources['used_memory_mb'] += memory_mb
            container = 'container_'+str(len(self.containers)+1).zfill(3)
            self.containers[container] = {'task': task, 'node': node, 'cpu': cpu,
                                          'memory_mb': memory_mb, 'active': True}
            self.record('ResourceManager', 'ALLOCATED', f'{container}: {task} @ {node}; CPU={cpu}, RAM={memory_mb} MiB')
            self.record(node, 'LAUNCHED', f'{container}: {task}')
            return container
        return None

    def release(self, container, status='COMPLETED'):
        info = self.containers[container]
        if not info['active']:
            return
        resources = self.nodes[info['node']]
        resources['used_cpu'] -= info['cpu']
        resources['used_memory_mb'] -= info['memory_mb']
        info['active'] = False
        self.record(info['node'], status, f'{container}: {info["task"]}; resource released')

    def run_tasks(self, tasks):
        if self.state != 'RUNNING':
            raise ValueError('Application is not running')
        # tasks is [(label, callable)]. Only allocated tasks may be submitted.
        pending = list(enumerate(tasks))
        results, active = {}, {}
        for _, (label, _) in pending:
            self.record('ApplicationMaster', 'REQUESTED', label+'; CPU=1, RAM=512 MiB')
        try:
            with ThreadPoolExecutor(max_workers=len(self.nodes)) as pool:
                while pending or active:
                    while pending:
                        index, (label, function) = pending[0]
                        container = self.allocate(label)
                        if container is None:
                            self.record('ResourceManager', 'WAITING', label+'; waiting for free CPU/RAM')
                            break
                        pending.pop(0)
                        active[pool.submit(function)] = (index, container)
                    if not active:
                        raise ValueError('No available node can satisfy the task request')
                    done, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in done:
                        index, container = active.pop(future)
                        try:
                            results[index] = future.result()
                        except Exception:
                            self.release(container, 'FAILED')
                            raise
                        self.release(container)
        except Exception:
            self.finish(False)
            raise
        return [results[index] for index in range(len(tasks))]

    def finish(self, success=True):
        if self.state in ('FINISHED', 'FAILED'):
            return
        for container in self.containers:
            self.release(container, 'COMPLETED' if success else 'STOPPED')
        self.state = 'FINISHED' if success else 'FAILED'
        self.record('ResourceManager', self.state, 'SUCCEEDED' if success else 'FAILED')

    def evidence(self):
        return {'application_id': self.application_id, 'state': self.state,
                'final_status': 'SUCCEEDED' if self.state == 'FINISHED' else self.state,
                'resource_units': 'logical CPU and MiB for the teaching scheduler',
                'nodes': self.nodes, 'containers': self.containers, 'events': self.events}


def print_yarn(evidence,detail=False):
    if not detail:
        print('YARN:',evidence['final_status'])
        print('Tugas:',', '.join(container['task']+' -> '+container['node']
              for container in evidence['containers'].values() if container['task']!='ApplicationMaster'))
        if any(event['event']=='WAITING' for event in evidence['events']):
            print('WAITING: Mapper B menunggu Mapper A selesai.')
        free = all(node['used_cpu']==0 and node['used_memory_mb']==0 for node in evidence['nodes'].values())
        print('Resource dilepas:', 'ya' if free else 'belum')
        return
    print('YARN mengatur jatah CPU/RAM agar setiap tugas mendapat tempat untuk berjalan.')
    print('1. Pekerjaan dikirim dan diterima. ID:', evidence['application_id'])
    print('2. Koordinator (ApplicationMaster) mendapat tempat di NM1.')
    print('3. Pengatur kapasitas (ResourceManager) memberi jatah; NodeManager menjalankan tugas:')
    for container in evidence['containers'].values():
        if container['task'] != 'ApplicationMaster':
            print('  ',container['task'],'->',container['node'],
                  '| jatah:',container['cpu'],'CPU dan',container['memory_mb'],'MiB RAM')
    if any(event['event']=='WAITING' for event in evidence['events']):
        print('   WAITING = menunggu: Mapper B baru mendapat tempat setelah Mapper A selesai.')
    if evidence['final_status']=='SUCCEEDED':
        print('4. Semua tugas selesai. FINISHED / SUCCEEDED = pekerjaan berhasil.')
    else:
        print('4. Status pekerjaan:',evidence['final_status'])
    free = all(node['used_cpu']==0 and node['used_memory_mb']==0 for node in evidence['nodes'].values())
    print('Jatah CPU/RAM sudah dilepas:', 'ya' if free else 'belum')
    if detail:
        print('Catatan lengkap urutan proses:')
        for event in evidence['events']:
            print(f" {event['sequence']:02d}. {event['actor']} {event['event']} | {event['detail']}")
