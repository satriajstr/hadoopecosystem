-- Overall rate is computed from counts, not the mean of district percentages.
SELECT COUNT(*) AS eligible_children,
       COALESCE(SUM(dose1), 0) AS dose1_children,
       COALESCE(SUM(dose3), 0) AS dose3_children,
       COALESCE(SUM(CASE WHEN dose1 = 1 AND dose3 = 0 THEN 1 ELSE 0 END), 0) AS dropout_children,
       COALESCE(SUM(CASE WHEN dose3 = 0 THEN 1 ELSE 0 END), 0) AS missed_dose3,
       COALESCE(SUM(CASE WHEN dose1 = 0 THEN 1 ELSE 0 END), 0) AS never_started_dose1,
       ROUND(100.0 * SUM(dose3) / NULLIF(COUNT(*), 0), 2) AS coverage_pct,
       ROUND(100.0 * (SUM(dose1) - SUM(dose3)) / NULLIF(SUM(dose1), 0), 2) AS dropout_pct
FROM vaccinations
WHERE birth_year = 2023 AND dose3_due = 1;
