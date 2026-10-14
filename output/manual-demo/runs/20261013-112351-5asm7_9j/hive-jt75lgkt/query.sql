-- Synthetic child registry, one row per child. Same query tested in SQLite.
-- Eligibility is an invented teaching flag, not a clinical schedule.
WITH cohort AS (
    SELECT * FROM vaccinations
    WHERE birth_year = 2023 AND dose3_due = 1
)
SELECT province, district, COUNT(*) AS eligible_children,
       SUM(dose1) AS dose1_children, SUM(dose3) AS dose3_children,
       ROUND(100.0 * SUM(dose3) / COUNT(*), 2) AS coverage_pct,
       ROUND(100.0 * (SUM(dose1) - SUM(dose3))
             / NULLIF(SUM(dose1), 0), 2) AS dropout_pct,
       SUM(CASE WHEN dose3 = 0 THEN 1 ELSE 0 END) AS missed_dose3
FROM cohort
GROUP BY province, district
ORDER BY coverage_pct ASC, province ASC, district ASC;
