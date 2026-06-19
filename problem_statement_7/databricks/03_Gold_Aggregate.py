# Databricks notebook source
# MAGIC %md
# MAGIC # FleetOS — Gold Layer: Analytics Aggregates

# COMMAND ----------
CATALOG = "fleet_os"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.gold")

# Truck summary
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.gold.truck_summary AS
SELECT
    truck_unit,
    COUNT(*) FILTER (WHERE doc_type='maintenance_invoice') AS maintenance_count,
    SUM(CAST(amount_total AS DOUBLE)) FILTER (WHERE doc_type='maintenance_invoice') AS total_maintenance_cost,
    MAX(date) FILTER (WHERE doc_type='maintenance_invoice') AS last_service_date,
    MAX(expiry_date) FILTER (WHERE doc_type='insurance') AS insurance_expiry,
    MAX(expiry_date) FILTER (WHERE doc_type='cdl') AS cdl_expiry,
    MIN(date) FILTER (WHERE doc_type='bill_of_sale_purchase') AS purchase_date
FROM {CATALOG}.silver.documents
WHERE truck_unit IS NOT NULL AND truck_unit != ''
GROUP BY truck_unit
""")

# Monthly spend
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.gold.monthly_spend AS
SELECT
    date_trunc('month', CAST(date AS DATE)) AS month,
    truck_unit,
    category,
    SUM(CAST(amount_total AS DOUBLE)) AS total_spend,
    COUNT(*) AS invoice_count
FROM {CATALOG}.silver.documents
WHERE doc_type='maintenance_invoice' AND date IS NOT NULL
GROUP BY 1,2,3
ORDER BY 1 DESC, 2
""")

# Expiring docs
spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.gold.expiring_documents AS
SELECT filename, doc_type, truck_unit, driver_name, expiry_date,
       datediff(CAST(expiry_date AS DATE), current_date()) AS days_until_expiry
FROM {CATALOG}.silver.documents
WHERE expiry_date IS NOT NULL
  AND CAST(expiry_date AS DATE) BETWEEN current_date() AND date_add(current_date(), 90)
ORDER BY expiry_date
""")

print("✓ Gold tables created")
