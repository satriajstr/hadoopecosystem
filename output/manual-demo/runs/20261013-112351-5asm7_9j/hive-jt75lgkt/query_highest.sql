WITH district_counts AS (
    SELECT province, district, COUNT(*) AS eligible_children,
           SUM(dose1) AS dose1_children, SUM(dose3) AS dose3_children,
           SUM(CASE WHEN dose1 = 1 AND dose3 = 0 THEN 1 ELSE 0 END) AS dropout_children,
           SUM(CASE WHEN dose3 = 0 THEN 1 ELSE 0 END) AS missed_dose3,
           SUM(CASE WHEN dose1 = 0 THEN 1 ELSE 0 END) AS never_started_dose1
    FROM vaccinations
    WHERE birth_year = 2023 AND dose3_due = 1
    GROUP BY province, district
)
SELECT province, district, eligible_children, dose1_children, dose3_children,
       dropout_children, missed_dose3, never_started_dose1,
       ROUND(100.0 * dose3_children / eligible_children, 2) AS coverage_pct,
       ROUND(100.0 * dropout_children / dose1_children, 2) AS dropout_pct
FROM district_counts
WHERE dose1_children > 0
-- Sort the unrounded rate. Ties use province/district for reproducible display.
ORDER BY 1.0 * dropout_children / dose1_children DESC, province ASC, district ASC
LIMIT 5;
