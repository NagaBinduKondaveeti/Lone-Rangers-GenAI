"""DuckDB schema — Bronze (raw) + Silver (structured) + Gold (aggregates)."""
import duckdb
from config import DB_PATH


def get_conn():
    return duckdb.connect(DB_PATH)


def init_schema():
    con = get_conn()

    # Bronze: raw extracted text
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze_documents (
            filename    VARCHAR PRIMARY KEY,
            file_path   VARCHAR,
            raw_text    TEXT,
            ingested_at TIMESTAMP DEFAULT current_timestamp
        )
    """)

    # Silver: structured entities
    con.execute("""
        CREATE TABLE IF NOT EXISTS silver_documents (
            filename        VARCHAR PRIMARY KEY,
            doc_type        VARCHAR,
            doc_number      VARCHAR,
            truck_unit      VARCHAR,
            vin             VARCHAR,
            date            DATE,
            amount_total    DOUBLE,
            vendor          VARCHAR,
            driver_name     VARCHAR,
            driver_license_no VARCHAR,
            expiry_date     DATE,
            make            VARCHAR,
            model           VARCHAR,
            year            INTEGER,
            plate_no        VARCHAR,
            policy_no       VARCHAR,
            title_no        VARCHAR,
            category        VARCHAR,
            amount_parts    DOUBLE,
            amount_labor    DOUBLE,
            technician      VARCHAR,
            insurer         VARCHAR,
            coverage_type   VARCHAR,
            liability_limit VARCHAR,
            buyer_name      VARCHAR,
            seller_name     VARCHAR,
            odometer        INTEGER,
            raw_json        JSON,
            processed_at    TIMESTAMP DEFAULT current_timestamp
        )
    """)

    # Gold: truck master
    con.execute("""
        CREATE OR REPLACE VIEW gold_truck_summary AS
        SELECT
            truck_unit,
            COUNT(*) FILTER (WHERE doc_type = 'maintenance_invoice') AS maintenance_count,
            SUM(amount_total) FILTER (WHERE doc_type = 'maintenance_invoice') AS total_maintenance_cost,
            MAX(date) FILTER (WHERE doc_type = 'maintenance_invoice') AS last_service_date,
            MAX(expiry_date) FILTER (WHERE doc_type = 'insurance') AS insurance_expiry,
            MAX(expiry_date) FILTER (WHERE doc_type = 'cdl') AS cdl_expiry,
            MIN(date) FILTER (WHERE doc_type = 'bill_of_sale_purchase') AS purchase_date,
            MAX(amount_total) FILTER (WHERE doc_type = 'bill_of_sale_purchase') AS purchase_price
        FROM silver_documents
        WHERE truck_unit IS NOT NULL AND truck_unit != ''
        GROUP BY truck_unit
        ORDER BY TRY_CAST(truck_unit AS INTEGER) NULLS LAST
    """)

    # Gold: monthly spend
    con.execute("""
        CREATE OR REPLACE VIEW gold_monthly_spend AS
        SELECT
            date_trunc('month', date) AS month,
            truck_unit,
            category,
            SUM(amount_total) AS total_spend,
            COUNT(*) AS invoice_count
        FROM silver_documents
        WHERE doc_type = 'maintenance_invoice'
          AND date IS NOT NULL
        GROUP BY 1, 2, 3
        ORDER BY 1 DESC, 2
    """)

    # Gold: expiring docs (next 90 days)
    con.execute("""
        CREATE OR REPLACE VIEW gold_expiring_documents AS
        SELECT
            filename,
            doc_type,
            truck_unit,
            driver_name,
            expiry_date,
            (expiry_date - current_date) AS days_until_expiry
        FROM silver_documents
        WHERE expiry_date IS NOT NULL
          AND expiry_date BETWEEN current_date AND current_date + INTERVAL 90 DAY
        ORDER BY expiry_date
    """)

    con.close()
    print("[DB] Schema initialized")
