"""Generate and execute DuckDB SQL from natural language via LLaMA-3.1-70B."""
import duckdb
from openai import OpenAI
from config import NVIDIA_API_KEY, NVIDIA_BASE_URL, MODEL, DB_PATH

client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)

SCHEMA = """
DuckDB tables and views for Sunflower Freight Lines LLC fleet management:

TABLE silver_documents:
  filename VARCHAR, doc_type VARCHAR, doc_number VARCHAR, truck_unit VARCHAR,
  vin VARCHAR, date DATE, amount_total DOUBLE, vendor VARCHAR,
  driver_name VARCHAR, driver_license_no VARCHAR, expiry_date DATE,
  make VARCHAR, model VARCHAR, year INTEGER, plate_no VARCHAR,
  policy_no VARCHAR, title_no VARCHAR, category VARCHAR,
  amount_parts DOUBLE, amount_labor DOUBLE, technician VARCHAR,
  insurer VARCHAR, coverage_type VARCHAR, liability_limit VARCHAR,
  buyer_name VARCHAR, seller_name VARCHAR, odometer INTEGER

doc_type values: bill_of_sale_purchase | bill_of_sale_sale | cdl | insurance |
                 maintenance_invoice | irp_card | certificate_of_title

VIEW gold_truck_summary:
  truck_unit, maintenance_count, total_maintenance_cost, last_service_date,
  insurance_expiry, cdl_expiry, purchase_date, purchase_price

VIEW gold_monthly_spend:
  month (DATE), truck_unit, category, total_spend, invoice_count

VIEW gold_expiring_documents:
  filename, doc_type, truck_unit, driver_name, expiry_date, days_until_expiry

TABLE bronze_documents:
  filename, file_path, raw_text

RULES:
- truck_unit is VARCHAR (e.g. '62', '84') — cast to INTEGER only for sorting
- Use date_trunc('month', date) for monthly grouping
- current_date for today
- Return readable column aliases
- No trailing semicolons
"""

SYSTEM = f"""You are a DuckDB SQL expert for a fleet management system.
{SCHEMA}
Return ONLY the raw SQL query. No explanation, no markdown, no semicolons."""


def run_sql_query(question: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": f"Question: {question}"}
        ],
        temperature=0.0,
        max_tokens=512,
    )
    sql = resp.choices[0].message.content.strip().rstrip(";")
    # Strip markdown if model added it
    if sql.startswith("```"):
        sql = sql.split("```")[1].lstrip("sql").strip().rstrip("`")

    try:
        con = duckdb.connect(DB_PATH)
        df  = con.execute(sql).df()
        con.close()
        return {"sql": sql, "rows": df.to_dict(orient="records"),
                "columns": list(df.columns), "error": None}
    except Exception as e:
        return {"sql": sql, "rows": [], "columns": [], "error": str(e)}
