-- Input: tabel WUENIC sebelum filter, berupa TSV tanpa header.
raw = LOAD '$INPUT' USING PigStorage('\t') AS (
    area_code:chararray, area_name:chararray, indicator:chararray, sex:chararray,
    year:int, coverage_pct:double, unit:chararray, observation_status:chararray,
    source_revision:chararray, age_group:chararray
);
selected = FILTER raw BY (area_code == 'IDN' OR area_code == 'MYS'
    OR area_code == 'THA' OR area_code == 'VNM' OR area_code == 'PHL') AND sex == '_T'
    AND unit == 'PCNT' AND observation_status == 'E'
    AND year >= 2020 AND year <= 2025
    AND (indicator == 'IM_DTP1' OR indicator == 'IM_DTP3')
    AND coverage_pct IS NOT NULL AND coverage_pct >= 0 AND coverage_pct <= 100;
by_country_year = GROUP selected BY (area_code, year);
counts = FOREACH by_country_year GENERATE FLATTEN(group) AS (area_code, year), COUNT_STAR(selected) AS indicator_rows;
ordered = ORDER counts BY area_code ASC, year ASC;
STORE selected INTO '$OUTPUT/filtered' USING PigStorage('\t');
STORE ordered INTO '$OUTPUT/by-country-year' USING PigStorage('\t');
