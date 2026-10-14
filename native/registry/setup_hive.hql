-- Registry table. Set --hivevar registry_path=THE_HDFS_CHILDREN_DIRECTORY.
CREATE DATABASE IF NOT EXISTS modul4_registry;
USE modul4_registry;
CREATE EXTERNAL TABLE IF NOT EXISTS vaccinations (
    child_id STRING, province STRING, district STRING, birth_date STRING,
    birth_year INT, dose3_due INT, dose1 INT, dose2 INT, dose3 INT, last_updated STRING
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE;
ALTER TABLE vaccinations SET LOCATION '${hivevar:registry_path}';
