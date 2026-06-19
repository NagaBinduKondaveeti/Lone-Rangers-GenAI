# Databricks notebook source
# MAGIC %md
# MAGIC # FleetOS — Silver Layer: Entity Extraction
# MAGIC Use Claude to extract structured entities from raw documents

# COMMAND ----------
# MAGIC %pip install anthropic

# COMMAND ----------
import json
import anthropic
from pyspark.sql.functions import udf, col
from pyspark.sql.types import MapType, StringType

ANTHROPIC_API_KEY = dbutils.secrets.get("fleet-os", "anthropic_api_key")
MODEL = "claude-sonnet-4-6"
CATALOG = "fleet_os"

SYSTEM = """You are a fleet document parser. Extract structured data from trucking company documents.
Return ONLY valid JSON with these fields (null if absent):
doc_type, doc_number, truck_unit, vin, date (YYYY-MM-DD), amount_total,
vendor, driver_name, driver_license_no, expiry_date (YYYY-MM-DD),
make, model, year, plate_no, policy_no, title_no, category,
amount_parts, amount_labor, technician, insurer, coverage_type, liability_limit

doc_type must be one of:
bill_of_sale_purchase|bill_of_sale_sale|cdl|insurance|maintenance_invoice|irp_card|certificate_of_title|unknown"""

def extract(filename, raw_text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM,
            messages=[{"role":"user","content": f"Filename: {filename}\n\n{raw_text[:3000]}"}]
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1].lstrip("json").strip()
        return json.loads(text)
    except:
        return {"doc_type": "unknown"}

# COMMAND ----------
bronze = spark.table(f"{CATALOG}.bronze.raw_documents").collect()

silver_rows = []
for row in bronze:
    entities = extract(row.filename, row.raw_text)
    silver_rows.append({
        "filename":         row.filename,
        "doc_type":         entities.get("doc_type"),
        "doc_number":       entities.get("doc_number"),
        "truck_unit":       str(entities.get("truck_unit") or "").strip() or None,
        "vin":              entities.get("vin"),
        "date":             entities.get("date"),
        "amount_total":     entities.get("amount_total"),
        "vendor":           entities.get("vendor"),
        "driver_name":      entities.get("driver_name"),
        "expiry_date":      entities.get("expiry_date"),
        "make":             entities.get("make"),
        "model":            entities.get("model"),
        "year":             str(entities.get("year") or ""),
        "plate_no":         entities.get("plate_no"),
        "category":         entities.get("category"),
        "amount_parts":     entities.get("amount_parts"),
        "amount_labor":     entities.get("amount_labor"),
        "technician":       entities.get("technician"),
        "insurer":          entities.get("insurer"),
        "raw_json":         json.dumps(entities),
    })

df_silver = spark.createDataFrame(silver_rows)
(df_silver.write.format("delta").mode("overwrite")
    .option("mergeSchema","true")
    .saveAsTable(f"{CATALOG}.silver.documents"))

print(f"✓ {len(silver_rows)} rows written to {CATALOG}.silver.documents")
