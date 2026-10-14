"""Full real dataset through two local mappers; verify per-country results."""
from pathlib import Path
import csv
import json
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from immunization_mapper import COUNTRIES, YEARS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/immunization-mapreduce'


def execute(script, text):
    return subprocess.run([sys.executable, str(ROOT/'code'/script)], input=text,
        capture_output=True, text=True, encoding='utf-8', check=True).stdout


def main(output_dir=None, input_path=None):
    out = Path(output_dir) if output_dir else OUT
    out.mkdir(parents=True, exist_ok=True)
    path = Path(input_path) if input_path else ROOT/'data/real/immunization_coverage_long.tsv'
    fields = ['area_code','area_name','indicator','sex','year','coverage_pct',
              'unit','observation_status','source_revision','age_group']
    with path.open(encoding='utf-8', newline='') as f:
        records = list(csv.DictReader(f, fieldnames=fields, delimiter='\t'))
    selected = [r for r in records if r['area_code'] in COUNTRIES and r['indicator']=='IM_DTP3'
        and r['sex']=='_T' and r['unit']=='PCNT' and r['observation_status']=='E'
        and int(r['year']) in YEARS]
    selected.sort(key=lambda r: (r['area_code'], int(r['year'])))
    for country in COUNTRIES:
        country_rows = [r for r in selected if r['area_code']==country]
        assert [int(r['year']) for r in country_rows] == list(YEARS)
        assert len({(r['source_revision'],r['age_group']) for r in country_rows}) == 1
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    chunks = [''.join(line for i,line in enumerate(lines) if i % 4 < 2),
              ''.join(line for i,line in enumerate(lines) if i % 4 >= 2)]
    mapped_chunks = [execute('immunization_mapper.py', chunk) for chunk in chunks]
    mapped = ''.join(mapped_chunks)
    shuffled = ''.join(line+'\n' for line in sorted(mapped.splitlines(), key=lambda s:s.split('\t')[0]))
    reduced = execute('immunization_reducer.py', shuffled)
    results = []
    for line in reduced.splitlines():
        key, total, count, mean = line.split('\t')
        country = key.split('|')[0]
        expected = sum(Decimal(r['coverage_pct']) for r in selected if r['area_code']==country)
        expected_mean = (expected/len(YEARS)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        assert Decimal(total)==expected and int(count)==len(YEARS) and Decimal(mean)==expected_mean
        results.append({'area_code':country, 'area_name':COUNTRIES[country], 'key':key,
                        'sum_of_year_percentages':str(total), 'year_count':int(count),
                        'mean_yearly_coverage_pct':str(mean)})
    assert {r['area_code'] for r in results} == set(COUNTRIES)
    assert len(results)==5 and len(mapped.splitlines())==len(selected)==30
    for name,content in [('input.tsv',text),('input-a.tsv',chunks[0]),('input-b.tsv',chunks[1]),
                         ('map-a.tsv',mapped_chunks[0]),('map-b.tsv',mapped_chunks[1]),
                         ('mapped.tsv',mapped),('shuffled.tsv',shuffled),('reduced.tsv',reduced)]:
        (out/name).write_text(content,encoding='utf-8')
    result = {'runtime':'Two local Python mapper subprocesses; local sort; Python reducer',
        'built_utc':datetime.now(timezone.utc).isoformat(), 'native_yarn':'NOT RUN',
        'source':'WHO/UNICEF WUENIC project snapshot, 2025 revision',
        'metric':'Unweighted arithmetic mean of annual DTP3 estimates per country, 2020-2025',
        'countries':COUNTRIES, 'source_input_rows':len(lines), 'selected_rows':len(selected),
        'mapper_input_rows':[len(chunk.splitlines()) for chunk in chunks],
        'mapper_output_rows':[len(chunk.splitlines()) for chunk in mapped_chunks],
        'input':[{'area_code':r['area_code'], 'area_name':r['area_name'],
                  'year':int(r['year']), 'coverage_pct':float(r['coverage_pct'])} for r in selected],
        'results':results,
        'interpretation':'Not pooled population coverage or a global mean; no infant population weights.'}
    (out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'LOCAL MAPREDUCE: {len(lines):,} input rows -> {len(selected)} DTP3 estimates -> {len(results)} countries')
    for row in results:
        print(row['area_code'], row['sum_of_year_percentages'], '/', row['year_count'], '=', row['mean_yearly_coverage_pct'], '%')
    print('Equal annual weights within each country; grouped by country and indicator metadata.')
    return result


if __name__ == '__main__':
    main()
