"""Test replica recovery and task scheduling against failures and resource limits."""
import tempfile
import threading
import unittest
from pathlib import Path
from prepare_dummy_dataset import ROOT
from concept_storage import write_blocks, read_file, repair_replicas, demonstrate_storage
from concept_yarn import YarnApplication


class ConceptChecks(unittest.TestCase):
    def workspace(self):
        (ROOT/'tmp').mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(prefix='concept-test-',dir=ROOT/'tmp')

    def test_byte_boundaries_replica_failure_and_repair(self):
        with self.workspace() as folder:
            root = Path(folder)
            source = root/'source'
            source.mkdir()
            original = ('anak José\tDTP3\n'*9).encode('utf-8')
            (source/'test.tsv').write_bytes(original)
            manifest = write_blocks(source,['test.tsv'],root/'hdfs',block_size=7)
            self.assertGreater(len(manifest['files']['test.tsv']['blocks']),2)
            self.assertEqual(read_file(root/'hdfs',manifest,'test.tsv')[0],original)
            manifest['nodes']['DN1'] = 'OFFLINE'
            result, trace = read_file(root/'hdfs',manifest,'test.tsv')
            self.assertEqual(result,original)
            self.assertTrue(all(row['node']!='DN1' for row in trace))
            repairs = repair_replicas(root/'hdfs',manifest)
            self.assertTrue(repairs)
            self.assertTrue(all(len(block['replicas'])==2 and 'DN1' not in block['replicas']
                                for block in manifest['files']['test.tsv']['blocks']))
            self.assertEqual(read_file(root/'hdfs',manifest,'test.tsv')[0],original)

    def test_corrupt_replica_fallback_then_unrecoverable_block(self):
        with self.workspace() as folder:
            root = Path(folder)
            (root/'test.csv').write_bytes(b'original data')
            manifest = write_blocks(root,['test.csv'],root/'hdfs',block_size=100)
            block = manifest['files']['test.csv']['blocks'][0]
            first, second = block['replicas']
            (root/'hdfs/datanodes'/first/block['id']).write_bytes(b'corrupt')
            data, trace = read_file(root/'hdfs',manifest,'test.csv')
            self.assertEqual(data,b'original data')
            self.assertEqual(trace[0]['node'],second)
            repair_replicas(root/'hdfs',manifest)
            self.assertEqual(read_file(root/'hdfs',manifest,'test.csv')[0],b'original data')
            for node in block['replicas']:
                (root/'hdfs/datanodes'/node/block['id']).unlink()
            with self.assertRaisesRegex(ValueError,'No healthy replica'):
                read_file(root/'hdfs',manifest,'test.csv')

    def test_storage_demo_reconstructs_empty_and_nonempty_files(self):
        with self.workspace() as folder:
            root = Path(folder)
            (root/'children.tsv').write_bytes(b'123\n'*9000)
            (root/'empty.csv').write_bytes(b'')
            result = demonstrate_storage(root,['children.tsv','empty.csv'],root/'hdfs',root/'snapshot')
            self.assertTrue(result['all_files_match_after_failure'])
            self.assertTrue(result['replication_restored'])
            self.assertEqual((root/'snapshot/children.tsv').read_bytes(),(root/'children.tsv').read_bytes())
            self.assertEqual((root/'snapshot/empty.csv').read_bytes(),b'')

    def assert_resources_valid(self, app):
        for event in app.events:
            for node in event['resources'].values():
                self.assertTrue(0 <= node['used_cpu'] <= node['cpu'])
                self.assertTrue(0 <= node['used_memory_mb'] <= node['memory_mb'])
        self.assertTrue(all(n['used_cpu']==0 and n['used_memory_mb']==0 for n in app.nodes.values()))

    def test_parallel_tasks_need_two_available_containers(self):
        app = YarnApplication()
        barrier = threading.Barrier(2)
        def task(value):
            barrier.wait(timeout=5)
            return value
        self.assertEqual(app.run_tasks([('Map A',lambda:task('a')),('Map B',lambda:task('b'))]),['a','b'])
        app.finish()
        self.assertEqual(app.state,'FINISHED')
        self.assert_resources_valid(app)
        containers = [c for c in app.containers.values() if c['task'].startswith('Map')]
        self.assertEqual(len({c['node'] for c in containers}),2)

    def test_resource_queue_orders_tasks_and_releases_capacity(self):
        app = YarnApplication(node_count=2)
        order = []
        def task(value):
            order.append(value)
            return value
        self.assertEqual(app.run_tasks([('Map A',lambda:task('a')),('Map B',lambda:task('b'))]),['a','b'])
        self.assertEqual(order,['a','b'])
        self.assertTrue(any(e['event']=='WAITING' for e in app.events))
        app.finish()
        self.assert_resources_valid(app)
        events = app.events
        finished_a = next(e['sequence'] for e in events if e['event']=='COMPLETED' and 'Map A' in e['detail'])
        started_b = next(e['sequence'] for e in events if e['event']=='LAUNCHED' and 'Map B' in e['detail'])
        self.assertLess(finished_a,started_b)

    def test_task_failure_marks_application_failed_and_releases_resources(self):
        app = YarnApplication()
        def fail():
            raise ValueError('task error')
        with self.assertRaisesRegex(ValueError,'task error'):
            app.run_tasks([('Bad mapper',fail),('Other mapper',lambda:'ok')])
        self.assertEqual(app.state,'FAILED')
        self.assertNotEqual(app.evidence()['final_status'],'SUCCEEDED')
        self.assert_resources_valid(app)
        with self.assertRaisesRegex(ValueError,'not running'):
            app.run_tasks([('Later mapper',lambda:'no')])


if __name__=='__main__':
    unittest.main()
