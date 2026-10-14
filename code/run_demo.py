"""Demo offline Modul 4. Python standard library saja, bukan cluster Hadoop."""
from pathlib import Path
import argparse
import csv
import html
import json
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIELDS = ["child_id", "province", "district", "birth_year", "dose3_due", "dose1", "dose3"]


def execute(script, stdin):
    return subprocess.run(
        [sys.executable, str(ROOT / "code" / script)],
        input=stdin, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout


def wordcount(text):
    mapped = execute("mapper.py", text)
    # Pada Hadoop, framework mengerjakan partition/shuffle/sort di cluster.
    # Di demo, sort hanya dilakukan di satu proses dan ditampung di RAM.
    shuffled = "".join(line + "\n" for line in sorted(mapped.splitlines(), key=lambda x: x.split("\t", 1)[0]))
    reduced = execute("reducer.py", shuffled)
    return mapped, shuffled, reduced


def load_records(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("Skema CSV tidak sesuai")
        records = []
        seen = set()
        for number, row in enumerate(reader, start=2):
            if None in row or any(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"Baris {number}: field hilang/berlebih/kosong")
            if row["child_id"] in seen:
                raise ValueError(f"Baris {number}: child_id duplikat")
            seen.add(row["child_id"])
            for name in FIELDS[3:]:
                row[name] = int(row[name])
            if any(row[name] not in (0, 1) for name in FIELDS[4:]):
                raise ValueError(f"Baris {number}: flag harus 0 atau 1")
            if row["dose3"] > row["dose1"]:
                raise ValueError(f"Baris {number}: dose3 tanpa dose1")
            records.append(row)
    return records


def query_coverage(records):
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE vaccinations (child_id TEXT PRIMARY KEY, province TEXT, district TEXT, birth_year INT, dose3_due INT, dose1 INT, dose3 INT)")
        connection.executemany("INSERT INTO vaccinations VALUES (?, ?, ?, ?, ?, ?, ?)",
                               [tuple(row[name] for name in FIELDS) for row in records])
        query = (ROOT / "native" / "coverage.sql").read_text(encoding="utf-8")
        return [dict(row) for row in connection.execute(query)]


def student_query():
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE students(id INT, name TEXT, gpa REAL)")
        with (ROOT / "data" / "students.csv").open(encoding="utf-8", newline="") as stream:
            connection.executemany("INSERT INTO students VALUES (?, ?, ?)", csv.reader(stream))
        return connection.execute("SELECT name, gpa FROM students WHERE gpa > 3.0 ORDER BY gpa DESC").fetchall()


def save_csv(filename, rows, fields):
    with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def case_demo(child_id):
    records = load_records(ROOT / "data" / "vaccinations.csv")
    cohort = [row for row in records if row["birth_year"] == 2023 and row["dose3_due"] == 1]
    missed = [row for row in cohort if row["dose3"] == 0]
    coverage = query_coverage(records)
    # Meniru konsep row-key lookup. Ini dictionary Python, bukan HBase.
    lookup_index = {row["child_id"]: row for row in records}
    lookup = lookup_index.get(child_id)
    save_csv("missed_doses.csv", missed, FIELDS)
    save_csv("coverage.csv", coverage, list(coverage[0]) if coverage else ["province", "district"])
    result = {"runtime": "Python + SQLite lokal; bukan Hadoop/Hive/Pig/HBase",
              "source_rows": len(records), "cohort_rows": len(cohort),
              "missed_count": len(missed), "coverage": coverage,
              "lookup_id": child_id, "lookup": lookup}
    (OUT / "case_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n[2] STUDI KASUS IMUNISASI - DATA SINTETIS")
    print(f"ETL Python: {len(records)} baris -> {len(cohort)} anak kohort 2023 eligible -> {len(missed)} belum dosis 3")
    print("ANALISIS SQL: CAKUPAN DAN DROPOUT")
    print(f"{'Distrik':<12} {'Eligible':>8} {'D1':>4} {'D3':>4} {'Cakupan':>10} {'Dropout':>10}")
    for row in coverage:
        dropout = "N/A" if row["dropout_pct"] is None else f"{row['dropout_pct']:.2f}%"
        print(f"{row['district']:<12} {row['eligible_children']:>8} {row['dose1_children']:>4} {row['dose3_children']:>4} {row['coverage_pct']:>9.2f}% {dropout:>10}")
    print(f"Lookup dictionary lokal untuk {child_id}: {json.dumps(lookup, ensure_ascii=False)}")
    return result


def report(result, reduced):
    escape = html.escape
    cards = "".join(
        f'<article><span>{escape(row["province"])}</span><h3>{escape(row["district"])}</h3>'
        f'<b>{row["coverage_pct"]:.2f}%</b><p>Cakupan dosis 3: {row["dose3_children"]}/{row["eligible_children"]} anak</p>'
        f'<div class="bar"><i style="width:{row["coverage_pct"]}%"></i></div>'
        f'<p>Dropout: {"N/A (D1 = 0)" if row["dropout_pct"] is None else str(row["dropout_pct"]) + "%"}</p></article>'
        for row in result["coverage"])
    codes = "".join(f'<details><summary>{escape(name)}</summary><pre>{escape((ROOT / name).read_text(encoding="utf-8"))}</pre></details>'
                    for name in ["code/mapper.py", "code/reducer.py", "native/coverage.sql", "native/etl_imunisasi.pig", "native/hbase_lookup.hbase"])
    text = f'''<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Modul 4 | Demo Hadoop Ecosystem</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f8;color:#182c3b;font:17px/1.65 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:44px 28px}}h1{{font-size:clamp(30px,5vw,52px);line-height:1.1;margin:12px 0 20px}}h2{{margin-top:42px}}.tag{{color:#14796f;font-weight:700;letter-spacing:2px;font-size:13px}}.notice{{background:#fff2d3;padding:16px 22px;border-left:4px solid #bb861f;border-radius:8px}}.flow{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}.flow span{{padding:12px 18px;background:#163e50;color:white;border-radius:10px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}}article{{background:white;border:1px solid #dee5e9;border-radius:16px;padding:24px}}article span{{font-size:13px;color:#687b87}}article h3{{margin:8px 0}}article b{{font-size:42px;color:#14796f}}article p{{font-size:15px}}.bar{{height:9px;background:#e7eef1;border-radius:5px;overflow:hidden}}.bar i{{display:block;height:100%;background:#14796f}}pre{{padding:22px;border-radius:12px;background:#122c3b;color:#e4f2f5;overflow-x:auto;font:14px/1.7 Consolas,monospace}}summary{{cursor:pointer;font-weight:600;padding:12px 0}}details{{border-bottom:1px solid #dbe3e9}}.small{{font-size:14px;color:#586f7b}}a{{color:#0b7168}}@media print{{body{{background:white}}main{{padding:0}}details{{break-inside:avoid}}}}
</style><main><div class="tag">BIG DATA / MODULE 04</div><h1>Bagaimana ekosistem Hadoop<br>mengolah data imunisasi?</h1>
<p>HDFS menyimpan data, YARN mengatur sumber daya, dan mesin pemrosesan mengubah data menjadi informasi.</p>
<div class="notice"><strong>Studi kasus: registri imunisasi sintetis.</strong> Ikuti alur penyimpanan, map–shuffle–reduce, analisis SQL, ETL, dan lookup individual.</div>
<div class="flow"><span>Ingestion: Sqoop / Flume</span><span>Penyimpanan: HDFS</span><span>ETL: Pig</span><span>Analisis: Hive</span><span>Lookup: HBase</span></div>
<p class="small">YARN mengelola job pemrosesan yang berjalan di atasnya. Oozie mengatur urutan workflow. Jalur di atas adalah contoh integrasi, bukan ketergantungan wajib semua tool.</p>
<h2>01 / Word Count</h2><p>Input → map (kata, 1) → shuffle &amp; sort → reduce (jumlah per kata).</p><pre>{escape(reduced)}</pre>
<h2>02 / Registri imunisasi</h2><p>{result["source_rows"]} baris awal → {result["cohort_rows"]} anak kohort 2023 yang sudah eligible → {result["missed_count"]} anak belum menerima dosis 3.</p><div class="grid">{cards}</div>
<p><strong>Interpretasi:</strong> Selatan mempunyai cakupan terendah. Utara juga memperlihatkan kehilangan kelanjutan dosis. Tengah memiliki dropout 0%, tetapi masih ada anak yang belum memulai dosis pertama.</p>
<p class="small">Cakupan = D3 / seluruh anak eligible × 100%. Dropout = (D1 − D3) / D1 × 100%. N/A berarti denominator nol, bukan dropout 0%. Angka menggambarkan dataset contoh, bukan estimasi populasi wilayah.</p>
<h2>03 / Lookup per anak</h2><pre>{escape(json.dumps(result["lookup"], indent=2, ensure_ascii=False))}</pre><p class="small">Lookup lokal memakai dictionary. File HBase Shell memperlihatkan column family dan contoh row key {escape(result["lookup_id"])}.</p>
<h2>04 / Kode yang dijelaskan saat demo</h2>{codes}
<h2>Kesimpulan</h2><p>Hive mempermudah query agregasi, Pig menggambarkan aliran transformasi, dan HBase melayani lookup individual. Demo ini menemukan pola cakupan; prediksi wabah memerlukan data dan model tambahan.</p>
<p class="small">Jalankan ulang: <code>python code/run_demo.py all</code>. Panduan narasi: <a href="../PANDUAN_PRESENTASI.md">PANDUAN_PRESENTASI.md</a>.</p></main></html>'''
    (OUT / "demo_report.html").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["all", "wordcount", "case"], nargs="?", default="all")
    parser.add_argument("--child", default="A004", help="ID anak untuk lookup lokal")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    print("MODUL 4 | DEMO ALUR HADOOP ECOSYSTEM")
    reduced = None
    if args.mode in ("all", "wordcount"):
        text = (ROOT / "data" / "sample.txt").read_text(encoding="utf-8")
        mapped, shuffled, reduced = wordcount(text)
        for name, value in [("mapped.tsv", mapped), ("shuffled.tsv", shuffled), ("wordcount.tsv", reduced)]:
            (OUT / name).write_text(value, encoding="utf-8")
        print("\n[1] WORD COUNT: INPUT\n" + text)
        print("MAP (9 pasangan):\n" + mapped)
        print("SHUFFLE/SORT LOKAL:\n" + shuffled)
        print("REDUCE:\n" + reduced)
        print("Lab query students (SQLite):", student_query())
    if args.mode in ("all", "case"):
        result = case_demo(args.child)
        if reduced is not None:
            report(result, reduced)
    print(f"\nHasil tersimpan di: {OUT}")


if __name__ == "__main__":
    main()
