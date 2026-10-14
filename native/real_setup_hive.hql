CREATE DATABASE IF NOT EXISTS modul4_real;
USE modul4_real;
CREATE EXTERNAL TABLE IF NOT EXISTS real_coverage_long (
    area_code STRING, area_name STRING, indicator STRING, sex STRING,
    year INT, coverage_pct DOUBLE, unit STRING, observation_status STRING,
    source_revision STRING, age_group STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE;
ALTER TABLE real_coverage_long SET LOCATION '${hivevar:hdfs_real}';
