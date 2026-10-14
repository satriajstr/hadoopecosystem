-- Input children.tsv has ten columns and no header.
raw = LOAD '$INPUT' USING PigStorage('\t') AS (
    child_id:chararray, province:chararray, district:chararray, birth_date:chararray,
    birth_year:int, dose3_due:int, dose1:int, dose2:int, dose3:int, last_updated:chararray
);
cohort = FILTER raw BY birth_year == 2023 AND dose3_due == 1;
missed = FILTER cohort BY dose3 == 0;
dropout = FILTER missed BY dose1 == 1;
not_started = FILTER missed BY dose1 == 0;
STORE cohort INTO '$OUTPUT/cohort' USING PigStorage('\t');
STORE missed INTO '$OUTPUT/missed-dose3' USING PigStorage('\t');
STORE dropout INTO '$OUTPUT/dropout-d1-d3' USING PigStorage('\t');
STORE not_started INTO '$OUTPUT/not-started-d1' USING PigStorage('\t');
