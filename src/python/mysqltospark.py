from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, count, round

mysql_jar = "/workspace/docker/build-context/assets/mysql-connector-j-8.0.33.jar"

spark = (
    SparkSession.builder
    .appName("mysql-to-spark-test")
    .master("spark://spark-master:7077")
    .config("spark.jars", mysql_jar)
    .getOrCreate()
)

jdbc_url = "jdbc:mysql://mysql:3306/zhitu?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=utf8"

props = {
    "user": "zhitu",
    "password": "zhitu123456",
    "driver": "com.mysql.cj.jdbc.Driver"
}

df = spark.read.jdbc(
    url=jdbc_url,
    table="clean_jobs",
    properties=props
)

print("MySQL clean_jobs 数据：")
df.show(truncate=False)

city_salary = df.groupBy("city").agg(
    count("*").alias("job_count"),
    round(avg("salary_avg"), 2).alias("avg_salary")
).orderBy("avg_salary", ascending=False)

print("Spark 城市平均薪资分析：")

city_salary.show(truncate=False)

spark.stop()