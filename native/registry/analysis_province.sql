SELECT province, COUNT(*) AS eligible_children,
       SUM(dose1) AS dose1_children, SUM(dose3) AS dose3_children,
       SUM(CASE WHEN dose1 = 1 AND dose3 = 0 THEN 1 ELSE 0 END) AS dropout_children,
       SUM(CASE WHEN dose3 = 0 THEN 1 ELSE 0 END) AS missed_dose3,
       SUM(CASE WHEN dose1 = 0 THEN 1 ELSE 0 END) AS never_started_dose1,
       ROUND(100.0 * SUM(dose3) / COUNT(*), 2) AS coverage_pct,
       ROUND(100.0 * (SUM(dose1) - SUM(dose3)) / NULLIF(SUM(dose1), 0), 2) AS dropout_pct
FROM vaccinations
WHERE birth_year = 2023 AND dose3_due = 1
GROUP BY province
ORDER BY 1.0 * (SUM(dose1) - SUM(dose3)) / NULLIF(SUM(dose1), 0) DESC, province ASC;
