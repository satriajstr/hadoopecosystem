-- Input CSV tanpa header. Parameter diisi dari folder HDFS run_hadoop.sh.
-- Dataset demo sudah divalidasi (ID unik, flag 0/1, dose3 <= dose1).
raw = LOAD '$INPUT' USING PigStorage(',') AS (
    child_id:chararray, province:chararray, district:chararray,
    birth_year:int, dose3_due:int, dose1:int, dose3:int
);
cohort = FILTER raw BY birth_year == 2023 AND dose3_due == 1;
missed = FILTER cohort BY dose3 == 0;
result = FOREACH missed GENERATE child_id, province, district, dose1, dose3;
STORE result INTO '$OUTPUT' USING PigStorage(',');
