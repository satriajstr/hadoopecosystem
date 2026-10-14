-- Query 1: jumlah observasi, bukan jumlah anak.
SELECT COUNT(*) AS observation_rows
FROM real_coverage_long;

-- Query 2: lima negara pada tahun yang sama; agregat regional tidak ikut.
SELECT area_code, area_name, year, indicator, coverage_pct
FROM real_coverage_long
WHERE area_code IN ('IDN','MYS','THA','VNM','PHL') AND year = 2025 AND sex = '_T'
      AND unit = 'PCNT' AND observation_status = 'E'
ORDER BY area_code, indicator;

-- Query 3: mean per negara. Keenam tahun berbobot sama, bukan mean global.
SELECT area_code, area_name, source_revision, age_group,
       SUM(coverage_pct) AS sum_of_year_percentages,
       COUNT(*) AS year_count, ROUND(AVG(coverage_pct),2) AS mean_yearly_dtp3_pct
FROM real_coverage_long
WHERE area_code IN ('IDN','MYS','THA','VNM','PHL')
      AND indicator = 'IM_DTP3' AND sex = '_T' AND unit = 'PCNT'
      AND observation_status = 'E' AND year BETWEEN 2020 AND 2025
GROUP BY area_code, area_name, source_revision, age_group
ORDER BY area_code;

-- Query 4: tren per negara; jangan menjumlahkan persentase sebagai cakupan.
SELECT area_code, area_name, year, coverage_pct AS dtp3_pct
FROM real_coverage_long
WHERE area_code IN ('IDN','MYS','THA','VNM','PHL') AND indicator = 'IM_DTP3' AND sex = '_T'
      AND unit = 'PCNT' AND observation_status = 'E'
      AND year BETWEEN 2020 AND 2025
ORDER BY year, area_code;

-- Query 5: pasangan indikator dan proxy dropout agregat, bukan riwayat anak.
WITH paired AS (
    SELECT area_code, area_name, year, source_revision, age_group,
           MAX(CASE WHEN indicator = 'IM_DTP1' THEN coverage_pct END) AS dtp1_pct,
           MAX(CASE WHEN indicator = 'IM_DTP3' THEN coverage_pct END) AS dtp3_pct
    FROM real_coverage_long
    WHERE area_code IN ('IDN','MYS','THA','VNM','PHL') AND sex = '_T' AND unit = 'PCNT'
          AND observation_status = 'E'
          AND year BETWEEN 2020 AND 2025
          AND indicator IN ('IM_DTP1', 'IM_DTP3')
    GROUP BY area_code, area_name, year, source_revision, age_group
)
SELECT area_code, area_name, year, dtp1_pct, dtp3_pct,
       ROUND(dtp1_pct - dtp3_pct, 2) AS gap_percentage_points,
       CASE WHEN dtp1_pct > 0 AND dtp3_pct <= dtp1_pct
            THEN ROUND(100.0 * (dtp1_pct - dtp3_pct) / NULLIF(dtp1_pct, 0), 2)
            ELSE NULL END AS dropout_proxy_pct
FROM paired
WHERE dtp1_pct IS NOT NULL AND dtp3_pct IS NOT NULL
ORDER BY year, area_code;
