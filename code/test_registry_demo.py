"""Check denominators, history integrity, grouping, and repeatable demo artifacts."""
import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import demo
from prepare_dummy_dataset import ROOT, DATA, generate, validate, digest, DEFAULT_CHILD, DEFAULT_CHILDREN
from indonesia_regions import REGIONS


class RegistryChecks(unittest.TestCase):
    def test_generated_history_matches_all_profiles(self):
        children,events = generate()
        self.assertEqual(len(children),1200)
        self.assertEqual(len(events),1662)
        self.assertEqual(len({r['province'] for r in children}),3)
        self.assertEqual(len({(r['province'],r['district']) for r in children}),6)
        cohort,missed = demo.filter_cohort(children)
        self.assertEqual(len(cohort),300)
        self.assertEqual(len(missed),145)
        self.assertEqual(sum(r['dose3'] for r in cohort),155)
        self.assertTrue(all(r['birth_year']==2023 and r['dose3_due']==1 for r in cohort))
        self.assertTrue(all(r['dose3']==0 for r in missed))
        self.assertEqual(generate(),(children,events))

    def test_coverage_dropouts_and_zero_denominator(self):
        rows = demo.sql_coverage(generate()[0])
        keyed = {r['district']:r for r in rows}
        self.assertEqual(keyed['Kabupaten Bandung']['coverage_pct'],50.0)
        self.assertEqual(keyed['Kabupaten Bandung']['dropout_pct'],44.44)
        self.assertEqual(keyed['Kabupaten Jember']['dropout_pct'],57.14)
        self.assertIsNone(keyed['Kabupaten Semarang']['dropout_pct'])
        self.assertEqual(keyed['Kabupaten Semarang']['eligible_children'],50)
        self.assertEqual(sum(r['eligible_children'] for r in rows),300)
        self.assertEqual(sum(r['missed_dose3'] for r in rows),145)
        self.assertEqual({r['district'] for r in rows if r['coverage_pct']<80},
                         {'Kabupaten Semarang','Kabupaten Jember','Kabupaten Bandung','Kabupaten Malang'})

    def test_same_district_name_in_two_provinces_stays_separate(self):
        children,_ = generate()
        rows = [copy.deepcopy(children[0]),copy.deepcopy(children[25])]
        for row,province in zip(rows,('P_A','P_B')):
            row['district'],row['province'] = 'Shared',province
        results = demo.sql_coverage(rows)
        self.assertEqual({r['province']:r['coverage_pct'] for r in results},{'P_A':100.0,'P_B':0.0})

    def test_sql_rankings_weighted_overall_and_empty_denominators(self):
        template = generate()[0][0]
        children = []
        for province,district,count,d1,d3 in [('P_A','A',100,1,1),('P_B','B',1,1,0),('P_C','C',1,0,0)]:
            for index in range(count):
                row = copy.deepcopy(template)
                row.update(child_id=f'T{len(children)}',province=province,district=district,
                           dose1=d1,dose2=d1,dose3=d3 if index<90 else 0)
                children.append(row)
        reports = demo.sql_analysis(children)
        total = reports['overall']
        self.assertEqual(total['eligible_children'],102)
        self.assertEqual(total['dose1_children'],101)
        self.assertEqual(total['dropout_children'],11)
        self.assertEqual(total['dropout_pct'],10.89)  # Weighted 11/101, not mean (10+100)/2.
        self.assertEqual([r['district'] for r in reports['highest']],['B','A'])
        self.assertEqual([r['district'] for r in reports['lowest']],['A','B'])
        self.assertEqual(reports['province'][-1]['dropout_pct'],None)
        self.assertEqual(sum(r['dropout_children'] for r in reports['province']),11)
        empty = demo.sql_analysis([])
        self.assertEqual(empty['highest'],[])
        self.assertEqual(empty['overall']['eligible_children'],0)
        self.assertIsNone(empty['overall']['dropout_pct'])
        self.assertIsNone(empty['overall']['coverage_pct'])
        with self.assertRaises(ValueError):
            demo.sql_analysis(children,0)

    def test_followup_partition_and_region_selection(self):
        children,_ = generate()
        cohort,missed,dropout,not_started = demo.filter_followup(children)
        self.assertEqual((len(cohort),len(missed),len(dropout),len(not_started)),(300,145,60,85))
        ids = lambda rows:{r['child_id'] for r in rows}
        self.assertEqual(ids(missed),ids(dropout)|ids(not_started))
        self.assertFalse(ids(dropout)&ids(not_started))
        selected = demo.filter_followup(children,'Jawa Barat','Kabupaten Bandung')
        self.assertEqual(tuple(map(len,selected)),(50,25,20,5))
        self.assertIn(DEFAULT_CHILD,ids(selected[2]))
        with self.assertRaises(ValueError):
            demo.filter_followup(children,district='Kabupaten Bandung')
        with self.assertRaises(ValueError):
            demo.filter_followup(children,'Jawa Tengah','Kabupaten Bandung')

    def test_lookup_history_empty_profile_and_absent_id(self):
        children,events = generate()
        found = demo.lookup(children,events,DEFAULT_CHILD)
        self.assertTrue(found['found'])
        self.assertEqual([r['dose_number'] for r in found['history']],[1,2])
        self.assertEqual([r['vaccination_date'] for r in found['history']],['2023-06-01','2023-07-01'])
        self.assertEqual(found['missing_due_doses'],['DTP3'])
        empty = demo.lookup(children,events,'D000401')
        self.assertTrue(empty['found'])
        self.assertEqual(empty['history'],[])
        self.assertEqual(empty['missing_due_doses'],['DTP1','DTP2','DTP3'])
        absent = demo.lookup(children,events,'NOT-IN-DATA')
        self.assertFalse(absent['found'])
        self.assertIsNone(absent['profile'])

    def test_invalid_registry_data_stops_processing(self):
        children,events = generate()
        cases = []
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        c.append(copy.deepcopy(c[0])); cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        e.append(copy.deepcopy(e[0])); cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        e[0]['child_id']='ORPHAN'; cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        c[0]['dose1']=0; cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        e.pop(); cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        e[1]['vaccination_date']='2023-05-01'; cases.append((c,e))
        c,e = copy.deepcopy(children),copy.deepcopy(events)
        c[0]['birth_year']=2022; cases.append((c,e))
        for number,(c,e) in enumerate(cases):
            with self.subTest(case=number), self.assertRaises(ValueError):
                validate(c,e)

    def test_mapper_reducer_empty_final_group_and_partial_counts(self):
        self.assertEqual(demo.execute('registry_mapper.py',''),'')
        self.assertEqual(demo.execute('registry_reducer.py',''),'')
        result = demo.execute('registry_reducer.py','A|X\t2\t1\t1\nA|X\t1\t1\t0\nB|Y\t1\t0\t0\n')
        self.assertEqual(result,'A|X\t3\t2\t1\t33.33\t50.00\nB|Y\t1\t0\t0\t0.00\t\\N\n')

    def test_actual_stages_repeat_preserve_sources_and_detect_tampering(self):
        names = ('children.csv','children.tsv','vaccination_events.csv','metadata.json')
        hashes = {name:digest(DATA/name) for name in names}
        expected_missed = len(demo.filter_cohort(demo.load(DATA)[0])[1])
        tmp = ROOT/'tmp'
        tmp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='registry-test-',dir=tmp) as folder:
            out = Path(folder).resolve()
            self.assertTrue(out.is_relative_to(ROOT.resolve()))
            with patch.object(demo,'OUT',out),contextlib.redirect_stdout(io.StringIO()):
                run = demo.storage()
                results = {name:demo.stage(name) for name in demo.STAGES}
                self.assertTrue(results['mapreduce']['matches_sql'])
                self.assertTrue(results['hive']['matches_mapreduce'])
                self.assertEqual(results['pig']['missed_dose3'],expected_missed)
                self.assertEqual(results['pig']['dropout_children'],results['hive']['analysis']['overall']['dropout_children'])
                self.assertEqual(results['hbase']['missing_due_doses'],['DTP3'])
                old = json.loads((run/'session.json').read_text(encoding='utf-8'))['last_jobs']
                files = {path:digest(path) for name in old.values() for path in (run/name).rglob('*') if path.is_file()}
                for name in demo.STAGES:
                    demo.stage(name)
                new = json.loads((run/'session.json').read_text(encoding='utf-8'))['last_jobs']
                self.assertTrue(all(old[name]!=new[name] for name in demo.STAGES))
                self.assertTrue(all(path.exists() and digest(path)==value for path,value in files.items()))
                another = demo.storage()
                self.assertNotEqual(run,another)
                self.assertTrue((run/'session.json').exists())
                self.assertFalse(demo.stage('hbase','NOT-IN-DATA')['found'])
                (another/'storage/children.tsv').write_text('tampered',encoding='utf-8')
                with self.assertRaises(ValueError):
                    demo.stage('hive')
        self.assertEqual({name:digest(DATA/name) for name in names},hashes)

    def test_configurable_size_provinces_and_unique_event_relationships(self):
        self.assertEqual(DEFAULT_CHILDREN,80137)
        children,events = generate(DEFAULT_CHILDREN,12)
        reference = json.loads((ROOT/'source/regions/bps_region_pairs.json').read_text(encoding='utf-8'))
        official_pairs = {(p,d.replace('BANYU ASIN','BANYUASIN')) for p,d in reference['pairs']}
        for province,district in {(r['province'],r['district']) for r in children}:
            self.assertIn((province.upper(),district.removeprefix('Kabupaten ').upper()),official_pairs)
        self.assertEqual((children[0]['province'],children[0]['district']),
                         ('Jawa Barat','Kabupaten Bandung'))
        self.assertEqual(len(REGIONS),38)
        largest_geography,_ = generate(15200,38)
        self.assertEqual(len({r['province'] for r in largest_geography}),38)
        self.assertEqual(len({(r['province'],r['district']) for r in largest_geography}),76)
        small_varied,small_events = generate(30400,38)
        self.assertEqual(len(small_varied),30400)
        validate(small_varied,small_events)
        self.assertEqual(len(children),80137)
        self.assertEqual(len({r['child_id'] for r in children}),80137)
        self.assertEqual(len({r['province'] for r in children}),12)
        self.assertEqual(len({(r['province'],r['district']) for r in children}),24)
        self.assertEqual(len(demo.filter_cohort(children)[0]),20035)
        self.assertEqual(len(events),112931)
        self.assertEqual(sum(row['dose3'] for row in demo.filter_cohort(children)[0]),10655)
        coverage = demo.sql_coverage(children)
        self.assertEqual(len({row['coverage_pct'] for row in coverage}),24)
        numeric_dropout = [row['dropout_pct'] for row in coverage if row['dropout_pct'] is not None]
        self.assertEqual(len(numeric_dropout),23)
        self.assertEqual(len(set(numeric_dropout)),23)
        self.assertEqual([row['district'] for row in coverage if row['dropout_pct'] is None],['Kabupaten Semarang'])
        bandung = next(row for row in coverage if row['district']=='Kabupaten Bandung')
        self.assertEqual(bandung['eligible_children'],832)
        self.assertEqual(bandung['coverage_pct'],50.36)
        self.assertEqual(bandung['dropout_pct'],43.91)
        self.assertTrue(all(len({r['district'] for r in children if r['province']==p})==2
                            for p in {r['province'] for r in children}))
        self.assertEqual(len(generate(1201,3)[0]),1201)
        self.assertEqual(len(generate(1200,1)[0]),1200)
        validate(children,events)
        with self.assertRaises(ValueError):
            generate(0,12)
        with self.assertRaises(ValueError):
            generate(30000,39)
        with self.assertRaises(ValueError):
            generate(1200,38)


if __name__=='__main__':
    unittest.main()
