"""Validasi hasil dan edge case yang bisa mengubah kesimpulan presentasi."""
from pathlib import Path
import tempfile
import unittest
from run_demo import ROOT, FIELDS, load_records, query_coverage, student_query, wordcount


class DemoChecks(unittest.TestCase):
    def test_wordcount_and_final_key(self):
        text = (ROOT / "data" / "sample.txt").read_text(encoding="utf-8")
        result = wordcount(text)[2]
        self.assertEqual(result, "hadoop\t3\nhdfs\t1\nhive\t3\npig\t1\nyarn\t1\n")
        self.assertEqual(wordcount("")[2], "")
        self.assertEqual(wordcount("satu satu\nsatu")[2], "satu\t3\n")

    def test_coverage_cohort_and_zero_denominator(self):
        rows = query_coverage(load_records(ROOT / "data" / "vaccinations.csv"))
        results = {row["district"]: row for row in rows}
        self.assertEqual(sum(row["eligible_children"] for row in rows), 18)
        self.assertEqual(results["Utara"]["coverage_pct"], 50.0)
        self.assertEqual(results["Utara"]["dropout_pct"], 40.0)
        self.assertEqual(results["Tengah"]["coverage_pct"], 66.67)
        self.assertEqual(results["Tengah"]["dropout_pct"], 0.0)
        self.assertIsNone(results["Selatan"]["dropout_pct"])
        self.assertEqual(sum(row["missed_dose3"] for row in rows), 11)

    def test_invalid_and_duplicate_records_stop_demo(self):
        header = ",".join(FIELDS) + "\n"
        cases = [
            "A001,P,D,2023,1,1,0\nA001,P,D,2023,1,1,0\n",
            "A001,P,D,2023,1,0,1\n",
            "A001,P,D,2023,1,2,0\n",
            "A001,P,D,2023,1,1\n",
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.csv"
            for case in cases:
                with self.subTest(case=case):
                    path.write_text(header + case, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_records(path)

    def test_students_strict_threshold(self):
        self.assertEqual(student_query(), [("Ani", 3.8), ("Citra", 3.5), ("Eka", 3.2)])


if __name__ == "__main__":
    unittest.main()
