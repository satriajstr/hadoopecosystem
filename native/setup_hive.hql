-- Jalankan dengan Beeline --hivevar hdfs_base=PATH_YANG_DICETAK_SCRIPT.
-- Nama database khusus demonstrasi.
CREATE DATABASE IF NOT EXISTS modul4_demo;
USE modul4_demo;

CREATE EXTERNAL TABLE IF NOT EXISTS students (
    id INT, name STRING, gpa DOUBLE
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE;
ALTER TABLE students SET LOCATION '${hivevar:hdfs_base}/students';

CREATE EXTERNAL TABLE IF NOT EXISTS vaccinations (
    child_id STRING, province STRING, district STRING,
    birth_year INT, dose3_due INT, dose1 INT, dose3 INT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE;
-- CSV tanpa header diunggah oleh run_hadoop.sh.
ALTER TABLE vaccinations SET LOCATION '${hivevar:hdfs_base}/vaccinations';

SELECT name, gpa FROM students WHERE gpa > 3.0 ORDER BY gpa DESC;
