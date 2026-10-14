"""Transitions and read-only boundaries of the live dashboard."""
import json
import tempfile
import unittest
from pathlib import Path
from dashboard_server import DashboardState, ROOT


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


class DashboardChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='dashboard-test-')
        self.root = Path(self.temp.name)
        self.latest = self.root/'latest.json'
        self.runs = self.root/'runs'
        self.runs.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def session(self,name):
        folder = self.runs/name
        save(folder/'session.json',{'run_id':name,'created_utc':'2026-10-12T00:00:00+00:00',
            'children':100,'vaccination_events':125,'cohort':2023,'synthetic':True,'last_jobs':{}})
        save(folder/'storage/metadata.json',{'provinces':1,'districts':2,'snapshot_date':'2026-10-01'})
        save(folder/'hdfs/results.json',{'initial':{'files':{'children.csv':{'blocks':[{}],'bytes':10}},
            'replication':2,'block_size_bytes':16384},'failed_node':'DN1','repairs':[{}],
            'all_files_match_after_failure':True,'replication_restored':True})
        save(self.latest,{'run_id':name,'dataset_kind':'dummy-registry-v1'})
        return folder

    def test_no_run_and_fresh_start_do_not_show_previous_results(self):
        state = DashboardState(self.runs,self.latest)
        self.assertEqual(state.snapshot()['state'],'empty')
        self.session('old-run')
        fresh = DashboardState(self.runs,self.latest)
        self.assertIsNone(fresh.snapshot()['run'])
        self.assertTrue(all(s['status']=='pending' for s in fresh.snapshot()['stages'].values()))
        resumed = DashboardState(self.runs,self.latest,fresh=False)
        self.assertEqual(resumed.snapshot()['run']['id'],'old-run')

    def test_new_storage_reveals_only_storage_and_new_session_clears_other_stages(self):
        state = DashboardState(self.runs,self.latest)
        run = self.session('first-run')
        first = state.snapshot()
        self.assertEqual(first['stages']['storage']['data']['blocks'],1)
        self.assertEqual(first['stages']['hive']['status'],'pending')
        save(run/'hive-job/results.json',{'results':[{'coverage_pct':0}],'analysis':{'overall':{'coverage_pct':0}}})
        # A completed file without a session commit is intentionally invisible.
        self.assertEqual(state.snapshot()['stages']['hive']['status'],'pending')
        session = json.loads((run/'session.json').read_text())
        session['last_jobs']['hive']='hive-job'
        save(run/'session.json',session)
        self.assertEqual(state.snapshot()['stages']['hive']['data']['results'][0]['coverage_pct'],0)
        self.session('next-run')
        self.assertEqual(state.snapshot()['stages']['hive']['status'],'pending')
        self.assertIsNone(state.snapshot()['stages']['hive']['data'])

    def test_cleared_latest_and_incomplete_writes_do_not_reuse_old_data(self):
        state = DashboardState(self.runs,self.latest)
        run = self.session('first-run')
        self.assertEqual(state.snapshot()['state'],'ready')
        self.latest.unlink()
        self.assertEqual(state.snapshot()['state'],'empty')
        save(self.latest,{'run_id':'first-run','dataset_kind':'dummy-registry-v1'})
        (run/'session.json').write_text('{',encoding='utf-8')
        self.assertEqual(state.snapshot()['state'],'waiting')
        self.assertIsNone(state.snapshot()['run'])

    def test_job_path_traversal_and_uncommitted_download_are_rejected(self):
        state = DashboardState(self.runs,self.latest)
        run = self.session('first-run')
        with self.assertRaises(ValueError):
            state.run_folder('../outside')
        with self.assertRaises(ValueError):
            state.job_folder(run,'hive','hive-../../outside')
        save(run/'hive-job/results.json',{'results':[]})
        with self.assertRaises(ValueError):
            state.download('/results/first-run/hive-job/results.json')
        with self.assertRaises(ValueError):
            state.download('/results/first-run/hive-job/session.json')

    def test_downloads_are_bound_to_latest_completed_job(self):
        state = DashboardState(self.runs,self.latest)
        run = self.session('first-run')
        save(run/'hive-job/results.json',{'results':[]})
        session = json.loads((run/'session.json').read_text())
        session['last_jobs']['hive']='hive-job'
        save(run/'session.json',session)
        path = state.download('/results/first-run/hive-job/results.json')
        self.assertEqual(path,run/'hive-job/results.json')
        self.session('second-run')
        with self.assertRaises(ValueError):
            state.download('/results/first-run/hive-job/results.json')

    def test_partial_job_is_waiting_instead_of_ready(self):
        state = DashboardState(self.runs,self.latest)
        run = self.session('first-run')
        (run/'hive-job').mkdir()
        (run/'hive-job/results.json').write_text('{',encoding='utf-8')
        session = json.loads((run/'session.json').read_text())
        session['last_jobs']['hive']='hive-job'
        save(run/'session.json',session)
        snapshot = state.snapshot()
        self.assertEqual(snapshot['stages']['storage']['status'],'ready')
        self.assertEqual(snapshot['stages']['hive']['status'],'waiting')
        self.assertIsNone(snapshot['stages']['hive']['data'])


if __name__=='__main__':
    unittest.main()
