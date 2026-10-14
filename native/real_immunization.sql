-- Grain input: wilayah/kelompok x indikator x sex x tahun.
-- Fokus IDN menghindari pencampuran negara dengan agregat regional.
WITH paired AS (
    SELECT area_code, area_name, year, source_revision, age_group,
           MAX(CASE WHEN indicator = 'IM_DTP1' THEN coverage_pct END) AS dtp1_pct,
           MAX(CASE WHEN indicator = 'IM_DTP3' THEN coverage_pct END) AS dtp3_pct
    FROM real_coverage_long
    WHERE area_code = 'IDN' AND sex = '_T' AND unit = 'PCNT'
          AND observation_status = 'E'
          AND indicator IN ('IM_DTP1', 'IM_DTP3')
    GROUP BY area_code, area_name, year, source_revision, age_group
)
SELECT area_code, area_name, year, dtp1_pct, dtp3_pct,
       ROUND(dtp1_pct - dtp3_pct, 2) AS gap_percentage_points,
       CASE WHEN dtp1_pct > 0 AND dtp3_pct <= dtp1_pct
            THEN ROUND(100.0 * (dtp1_pct - dtp3_pct)
                       / NULLIF(dtp1_pct, 0), 2)
            ELSE NULL END AS dropout_proxy_pct,
       source_revision
FROM paired
WHERE dtp1_pct IS NOT NULL AND dtp3_pct IS NOT NULL
ORDER BY year;
