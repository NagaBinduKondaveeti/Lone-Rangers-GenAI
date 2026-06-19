"""Load extracted entities into DuckDB."""
import json
from datetime import datetime
from db.schema import get_conn, init_schema

_initialized = True   # schema is initialized by run_pipeline before threads start

def _ensure_init():
    pass  # no-op — init happens once in main thread

def _parse_date(val):
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except Exception:
            pass
    return None

def _parse_float(val):
    if val is None:
        return None
    try:
        return float(str(val).replace("$","").replace(",","").strip())
    except Exception:
        return None

def _parse_int(val):
    if val is None:
        return None
    try:
        return int(str(val).replace(",","").strip())
    except Exception:
        return None

def upsert_document(entities: dict):
    _ensure_init()
    con = get_conn()
    try:
        _do_upsert(con, entities)
    finally:
        con.close()


def _do_upsert(con, entities: dict):

    filename  = entities.get("filename", "")
    raw_text  = entities.get("raw_text", "")
    file_path = entities.get("file_path", "")

    # Bronze
    con.execute("""
        INSERT OR REPLACE INTO bronze_documents (filename, file_path, raw_text)
        VALUES (?, ?, ?)
    """, [filename, file_path, raw_text])

    # Silver
    con.execute("""
        INSERT OR REPLACE INTO silver_documents (
            filename, doc_type, doc_number, truck_unit, vin, date, amount_total,
            vendor, driver_name, driver_license_no, expiry_date,
            make, model, year, plate_no, policy_no, title_no,
            category, amount_parts, amount_labor, technician,
            insurer, coverage_type, liability_limit,
            buyer_name, seller_name, odometer, raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [
        filename,
        entities.get("doc_type"),
        entities.get("doc_number"),
        str(entities.get("truck_unit") or "").strip() or None,
        entities.get("vin"),
        _parse_date(entities.get("date")),
        _parse_float(entities.get("amount_total")),
        entities.get("vendor"),
        entities.get("driver_name"),
        entities.get("driver_license_no"),
        _parse_date(entities.get("expiry_date")),
        entities.get("make"),
        entities.get("model"),
        _parse_int(entities.get("year")),
        entities.get("plate_no"),
        entities.get("policy_no"),
        entities.get("title_no"),
        entities.get("category"),
        _parse_float(entities.get("amount_parts")),
        _parse_float(entities.get("amount_labor")),
        entities.get("technician"),
        entities.get("insurer"),
        entities.get("coverage_type"),
        entities.get("liability_limit"),
        entities.get("buyer_name"),
        entities.get("seller_name"),
        _parse_int(entities.get("odometer")),
        json.dumps(entities),
    ])
