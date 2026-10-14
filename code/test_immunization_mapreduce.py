"""Verify filter semantics, final-key flushing and weighted sum/count reduction."""
import unittest
from run_immunization_mapreduce import execute


def row(area='IDN', indicator='IM_DTP3', year='2025', coverage='82', sex='_T'):
    return '\t'.join((area,'Indonesia',indicator,sex,year,coverage,'PCNT','E','revision','M12T23'))+'\n'


class ImmunizationChecks(unittest.TestCase):
    def test_mapper_filters_and_preserves_zero(self):
        text = row(coverage='0')+row(area='USA')+row(indicator='IM_DTP1')+row(year='2019')+row(sex='F')+row(coverage='\\N')
        self.assertEqual(execute('immunization_mapper.py',text), 'IDN|IM_DTP3|_T|PCNT|E|revision|M12T23\t0\t1\n')

    def test_reducer_sum_count_not_mean_of_partial_means(self):
        # Unequal batch sizes: (80/1 + 120/2)/2 = 70 is wrong; 200/3 = 66.67.
        text = 'A\t80\t1\nA\t120\t2\nB\t0\t1\n'
        self.assertEqual(execute('immunization_reducer.py',text),'A\t200\t3\t66.67\nB\t0\t1\t0.00\n')
        self.assertEqual(execute('immunization_reducer.py',''),'')

    def test_country_and_revision_keys_stay_separate(self):
        text = row(coverage='80')+row(area='MYS',coverage='90')+row(coverage='60').replace('revision','other-revision')
        mapped = execute('immunization_mapper.py',text)
        reduced = execute('immunization_reducer.py','\n'.join(sorted(mapped.splitlines()))+'\n')
        self.assertEqual(len(reduced.splitlines()),3)
        self.assertIn('MYS|IM_DTP3|_T|PCNT|E|revision|M12T23\t90\t1\t90.00',reduced)


if __name__ == '__main__':
    unittest.main()
