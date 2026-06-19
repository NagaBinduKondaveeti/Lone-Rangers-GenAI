# Databricks notebook source
# MAGIC %md
# MAGIC # FleetOS — Bronze Layer: PDF Ingestion
# MAGIC Ingest raw PDFs into Delta Lake bronze table

# COMMAND ----------
# MAGIC %pip install pdfplumber openai chromadb sentence-transformers

# COMMAND ----------
import os, json
from pathlib import Path
import pdfplumber
from pyspark.sql import SparkSession
from pyspark.sql.functions import lit, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, TimestampType

spark = SparkSession.builder.getOrCreate()

PDF_FOLDER = "/dbfs/FileStore/fleet_docs/"  # upload PDFs here
CATALOG    = "fleet_os"
SCHEMA_DB  = "bronze"

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA_DB}")

# COMMAND ----------
def extract_text(path):
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
    except Exception as e:
        return f"[ERROR] {e}"

records = []
for p in Path(PDF_FOLDER).glob("*.pdf"):
    records.append({
        "filename": p.name,
        "file_path": str(p),
        "raw_text": extract_text(str(p)),
    })

print(f"Extracted {len(records)} PDFs")

# COMMAND ----------
schema = StructType([
    StructField("filename",  StringType()),
    StructField("file_path", StringType()),
    StructField("raw_text",  StringType()),
])

df = spark.createDataFrame(records, schema=schema).withColumn("ingested_at", current_timestamp())

(df.write
   .format("delta")
   .mode("overwrite")
   .option("mergeSchema", "true")
   .saveAsTable(f"{CATALOG}.{SCHEMA_DB}.raw_documents"))

print(f"✓ Wrote {df.count()} rows to {CATALOG}.{SCHEMA_DB}.raw_documents")
