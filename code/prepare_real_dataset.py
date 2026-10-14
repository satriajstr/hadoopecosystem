"""Unduh dan siapkan data resmi UNICEF DTP1/DTP3; seluruh output di root proyek.

Python standard library saja. Default menggunakan snapshot lokal jika tersedia.
Data berupa estimasi agregat wilayah/kelompok dan tahun, bukan rekam anak.
"""
from pathlib import Path
from urllib.request import urlopen
from datetime import datetime, timezone
from collections import Counter
import argparse
import csv
import hashlib
import json
import math
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://sdmx.data.unicef.org/ws/public/sdmxapi/rest/data/"
       "UNICEF,GLOBAL_DATAFLOW,1.0/.IM_DTP1+IM_DTP3."
       "?format=sdmx-json&startPeriod=1980&endPeriod=2025")
RAW = ROOT / "source" / "real" / "unicef_dtp1_dtp3_1980_2025.json"
DATA = ROOT / "data" / "real"
OUT = ROOT / "output" / "real"
FIELDS = ["area_code", "area_name", "indicator", "sex", "year", "coverage_pct",
          "unit", "observation_status", "source_revision", "age_group"]


def decode(payload):
    content = payload["data"]
    structure = content["structure"]
    series_dims = structure["dimensions"]["series"]
    observation_dims = structure["dimensions"]["observation"]
    attrs = structure["attributes"]["observation"]
    if [d["id"] for d in series_dims] != ["REF_AREA", "INDICATOR", "SEX"]:
        raise ValueError("Urutan dimensi sumber berubah")
    if [d["id"] for d in observation_dims] != ["TIME_PERIOD"]:
        raise ValueError("Dimensi waktu sumber berubah")
    rows = []
    for dataset in content["dataSets"]:
        for key, series in dataset["series"].items():
            indexes = key.split(":")
            if len(indexes) != len(series_dims):
                raise ValueError("Key series tidak sesuai skema")
            dimensions = {dim["id"]: dim["values"][int(index)]
                          for dim, index in zip(series_dims, indexes)}
            for time_index, observation in series["observations"].items():
                attribute_values = {}
                if len(observation) != len(attrs) + 1:
                    raise ValueError("Atribut observation tidak sesuai skema")
                for attr, index in zip(attrs, observation[1:]):
                    attribute_values[attr["id"]] = None if index is None else attr["values"][index]["id"]
                year = int(observation_dims[0]["values"][int(time_index)]["id"])
                raw_value = observation[0]
                value = None if raw_value is None else float(raw_value)
                rows.append({
                    "area_code": dimensions["REF_AREA"]["id"],
                    "area_name": dimensions["REF_AREA"]["name"],
                    "indicator": dimensions["INDICATOR"]["id"],
                    "sex": dimensions["SEX"]["id"], "year": year,
                    "coverage_pct": value, "unit": attribute_values.get("UNIT_MEASURE"),
                    "observation_status": attribute_values.get("OBS_STATUS"),
                    "source_revision": attribute_values.get("DATA_SOURCE"),
                    "age_group": attribute_values.get("AGE"),
                })
    return sorted(rows, key=lambda row: (row["area_code"], row["year"], row["indicator"], row["sex"]))


def profile(rows):
    keys = Counter((r["area_code"], r["indicator"], r["sex"], r["year"]) for r in rows)
    duplicate_keys = sum(1 for count in keys.values() if count > 1)
    invalid_values = sum(r["coverage_pct"] is not None and
                         (not math.isfinite(r["coverage_pct"]) or not 0 <= r["coverage_pct"] <= 100) for r in rows)
    if duplicate_keys or invalid_values:
        raise ValueError(f"Duplikat key={duplicate_keys}; coverage tidak valid={invalid_values}")
    if set(r["indicator"] for r in rows) != {"IM_DTP1", "IM_DTP3"}:
        raise ValueError("Indikator sumber tidak sesuai")
    if {r["unit"] for r in rows} != {"PCNT"}:
        raise ValueError("Satuan sumber tidak seluruhnya persentase")
    pairs = {}
    for row in rows:
        pairs.setdefault((row["area_code"], row["sex"], row["year"]), {})[row["indicator"]] = row
    incomplete = 0
    inconsistent = 0
    incomplete_keys = []
    inconsistent_details = []
    for key, pair in pairs.items():
        if set(pair) != {"IM_DTP1", "IM_DTP3"} or any(r["coverage_pct"] is None for r in pair.values()):
            incomplete += 1
            incomplete_keys.append({"area_code": key[0], "sex": key[1], "year": key[2]})
            continue
        a, b = pair["IM_DTP1"], pair["IM_DTP3"]
        if a["age_group"] != b["age_group"] or a["source_revision"] != b["source_revision"]:
            raise ValueError("Pasangan DTP1/DTP3 tidak memiliki cakupan metadata yang sama")
        inconsistent += b["coverage_pct"] > a["coverage_pct"]
        if b["coverage_pct"] > a["coverage_pct"]:
            inconsistent_details.append({"area_code": key[0], "sex": key[1], "year": key[2],
                                         "dtp1_pct": a["coverage_pct"], "dtp3_pct": b["coverage_pct"]})
    return {
        "rows": len(rows), "area_or_group_count": len({r["area_code"] for r in rows}),
        "year_min": min(r["year"] for r in rows), "year_max": max(r["year"] for r in rows),
        "duplicate_keys": duplicate_keys, "invalid_coverage_values": invalid_values,
        "missing_coverage_values": sum(r["coverage_pct"] is None for r in rows),
        "missing_by_column": {name: sum(r[name] is None or r[name] == "" for r in rows) for name in FIELDS},
        "incomplete_dtp_pairs": incomplete, "dtp3_greater_than_dtp1_pairs": inconsistent,
        "incomplete_pair_keys": incomplete_keys, "dtp3_greater_than_dtp1_details": inconsistent_details,
        "observation_statuses": sorted({r["observation_status"] for r in rows}),
        "source_revisions": sorted({r["source_revision"] for r in rows}),
        "age_groups_as_published": sorted({r["age_group"] for r in rows}),
        "caveat": "REF_AREA mencakup negara dan kelompok agregat; jangan menjumlahkan persentase atau menyebut semua wilayah sebagai negara.",
    }


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def indonesia_query(rows):
    sql = (ROOT / "native" / "real_immunization.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE real_coverage_long (area_code TEXT, area_name TEXT, indicator TEXT, sex TEXT, year INT, coverage_pct REAL, unit TEXT, observation_status TEXT, source_revision TEXT, age_group TEXT)")
        conn.executemany("INSERT INTO real_coverage_long VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         [tuple(r[name] for name in FIELDS) for r in rows])
        return [dict(row) for row in conn.execute(sql)]


def prepare():
    rows = decode(json.loads(RAW.read_text(encoding="utf-8")))
    checks = profile(rows)
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(DATA / "immunization_coverage_long.csv", rows, FIELDS)
    indonesia = [r for r in rows if r["area_code"] == "IDN"]
    if not indonesia:
        raise ValueError("Indonesia tidak ditemukan dalam sumber")
    write_csv(DATA / "indonesia_dtp_long.csv", indonesia, FIELDS)
    # TSV tanpa header untuk external table Hive; metadata asli tetap dipertahankan.
    with (DATA / "immunization_coverage_long.tsv").open("w", encoding="utf-8", newline="") as stream:
        for row in rows:
            values = ["\\N" if row[name] is None else str(row[name]) for name in FIELDS]
            if any("\t" in value or "\n" in value or "\r" in value for value in values):
                raise ValueError("Field sumber tidak aman untuk TSV sederhana")
            stream.write("\t".join(values) + "\n")
    results = indonesia_query(rows)
    write_csv(OUT / "indonesia_coverage_dropout.csv", results, list(results[0]))
    checks["indonesia_long_rows"] = len(indonesia)
    checks["indonesia_result_years"] = len(results)
    checks["raw_sha256"] = hashlib.sha256(RAW.read_bytes()).hexdigest()
    (OUT / "quality_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    print("SUMBER NYATA: WHO/UNICEF WUENIC; estimasi agregat, bukan registri per anak")
    print(f"{len(rows):,} observasi | {checks['area_or_group_count']} wilayah/kelompok | {checks['year_min']}-{checks['year_max']}")
    print(f"Duplikat key: {checks['duplicate_keys']} | coverage kosong: {checks['missing_coverage_values']} | di luar 0-100: {checks['invalid_coverage_values']}")
    print(f"Indonesia: {len(indonesia)} observasi; {len(results)} tahun berpasangan")
    print("SQL aktual dijalankan dengan SQLite lokal; belum dengan Hive.")
    for row in results[-11:]:
        print(row)
    print("CSV utama:", DATA / "immunization_coverage_long.csv")
    return checks, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Unduh snapshot API baru; default memakai snapshot yang tersedia")
    args = parser.parse_args()
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if args.refresh or not RAW.exists():
        with urlopen(URL, timeout=45) as response:
            raw = response.read()
        payload = json.loads(raw)
        profile(decode(payload))  # Validasi sebelum mengganti snapshot sebelumnya.
        RAW.write_bytes(raw)
        provenance = {
            "publisher": "WHO/UNICEF", "dataset": "WUENIC DTP1/DTP3 via UNICEF GLOBAL_DATAFLOW",
            "api_url": URL, "source_page": "https://data.unicef.org/resources/dataset/immunization/",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "api_prepared_as_published": payload.get("meta", {}).get("prepared"),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
        }
        (RAW.parent / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    prepare()


if __name__ == "__main__":
    main()
