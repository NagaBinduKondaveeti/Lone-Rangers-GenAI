"""
Rule-based entity extractor — covers all 6 discovered doc types for Sunflower Freight Lines.
No API calls needed.
"""
import re
from datetime import datetime

VIN_RE  = re.compile(r'\b([A-HJ-NPR-Z0-9]{17})\b')
DATE_RE = re.compile(
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2},\s+\d{4}\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', re.I)

def _first(pat, text, grp=1, flags=re.IGNORECASE):
    m = re.search(pat, text, flags)
    return m.group(grp).strip() if m else None

def _parse_date(raw):
    if not raw: return None
    for fmt in ('%B %d, %Y','%m/%d/%Y','%Y-%m-%d','%b %d, %Y'):
        try: return datetime.strptime(raw.strip(), fmt).strftime('%Y-%m-%d')
        except: pass
    return None

def _amt(raw):
    if not raw: return None
    try: return float(str(raw).replace('$','').replace(',','').strip())
    except: return None

def _classify(text):
    t = text.upper()
    if 'CERTIFICATE OF TITLE' in t:                   return 'certificate_of_title'
    if 'COMMERCIAL DRIVER LICENSE' in t:               return 'cdl'
    if 'INSURANCE IDENTIFICATION CARD' in t or 'AUTOMOBILE INSURANCE' in t: return 'insurance'
    if 'INTERNATIONAL REGISTRATION PLAN' in t or ('CARRY IN CAB' in t and 'PLATE' in t): return 'irp_card'
    if 'INTERNATIONAL FUEL TAX AGREEMENT' in t or 'IFTA' in t: return 'ifta_return'
    if 'HEAVY HIGHWAY VEHICLE USE TAX' in t or 'FORM 2290' in t or ('OMB' in t and '2290' in t): return 'form_2290'
    if 'EQUIPMENT LEASE AGREEMENT' in t or 'MOTOR VEHICLE / EQUIPMENT LEASE' in t: return 'lease_agreement'
    if 'BILL OF SALE' in t:
        return 'bill_of_sale_sale' if ('(SALE)' in t or 'SALE\nMOTOR' in t) and 'PURCHASE' not in t else 'bill_of_sale_purchase'
    if 'FUEL' in t and 'RECEIPT' in t:                 return 'fuel_receipt'
    if 'INVOICE' in t:                                 return 'maintenance_invoice'
    return 'unknown'

def _bill_of_sale(text):
    vins   = VIN_RE.findall(text)
    dates  = DATE_RE.findall(text)
    amts   = re.findall(r'\$([\d,]+\.?\d{0,2})', text)
    return {
        'truck_unit':   _first(r'Fleet Unit No\.\s*(\d+)', text) or _first(r'Unit\s*[:#]\s*(\d+)', text),
        'doc_number':   _first(r'Document No\.\s*([A-Z0-9\-]+)', text),
        'date':         _parse_date(dates[0]) if dates else None,
        'amount_total': _amt(amts[0]) if amts else None,
        'vin':          vins[0] if vins else None,
        'buyer_name':   _first(r'Buyer[:\s]+([A-Za-z\s,\.]+?)(?:\n|Phone)', text),
        'seller_name':  _first(r'Seller[:\s]+([A-Za-z\s,\.]+?)(?:\n|Phone)', text),
    }

def _cdl(text):
    nm   = re.search(r'\n1([A-Z]+)\n\d?([A-Z]+)', text)
    name = f"{nm.group(2).title()} {nm.group(1).title()}" if nm else \
           _first(r'SIGNATURE OF LICENSEE\s*\n([A-Za-z ]+)', text)
    # Dates are on the line AFTER "3 DOB 4a ISS 4b EXP"
    dm   = re.search(r'3 DOB 4a ISS 4b EXP\n(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})', text)
    return {
        'driver_name':       name,
        'driver_license_no': _first(r'\b([A-Z]\d{2}-\d{2}-\d{4})\b', text),
        'date':              _parse_date(dm.group(2)) if dm else None,
        'expiry_date':       _parse_date(dm.group(3)) if dm else None,
    }

def _insurance(text):
    dates = DATE_RE.findall(text)
    vins  = VIN_RE.findall(text)
    unit  = _first(r'UNIT\s*[#\s]*(\d+)', text)
    limit = _first(r'\$([\d,]+(?:\.\d{2})?)\s*Combin', text) or _first(r'LIABILITY LIMIT\s+\$([\d,]+)', text)
    return {
        'truck_unit':     unit,
        'policy_no':      _first(r'POLICY NUMBER\s+([A-Z0-9\-\s]+?)(?:\n|COVERAGE)', text),
        'date':           _parse_date(dates[0]) if dates else None,
        'expiry_date':    _parse_date(dates[1]) if len(dates) > 1 else None,
        'vin':            vins[0] if vins else None,
        'insurer':        text.strip().split('\n')[0].strip(),
        'liability_limit':f'${limit}' if limit else None,
        'coverage_type':  _first(r'(Commercial Auto Liability|Cargo|Physical Damage)', text),
    }

def _invoice(text):
    lines  = [l.strip() for l in text.split('\n') if l.strip()]
    vendor = lines[0] if lines else None
    # Unit appears in PO number (PO-{unit}-{seq}) or after table header "I\n{unit}"
    unit   = (_first(r'PO\s*NO\.\s+PO-(\d+)-', text) or
              _first(r'UNIT\s+#\s+CATEGORY[^\n]*\nI\n(\d+)', text) or
              _first(r'\nI\n(\d+)\s+\w', text) or
              _first(r'UNIT\s*[#:]\s*(\d+)', text))
    vins   = VIN_RE.findall(text)
    dates  = DATE_RE.findall(text)
    total  = _first(r'TOTAL\s+\$([\d,]+\.?\d{0,2})', text)
    labor  = _first(r'LABOR\s+\$([\d,]+\.?\d{0,2})', text)
    parts  = _first(r'SUBTOTAL\s+\$([\d,]+\.?\d{0,2})', text)
    cat    = _first(r'\nI\n\d+\s+([A-Za-z/&]+)\s+A\s+PO-', text) or _first(r'CATEGORY\s+([A-Za-z/&\- ]+?)(?:\n|PDO)', text)
    return {
        'truck_unit':   unit,
        'vendor':       vendor,
        'doc_number':   _first(r'INVOICE NO\.\s+([A-Z0-9\-]+)', text),
        'date':         _parse_date(dates[0]) if dates else None,
        'amount_total': _amt(total),
        'amount_labor': _amt(labor),
        'amount_parts': _amt(parts),
        'category':     cat.strip() if cat else None,
        'technician':   _first(r'TECHNICIAN\s+([A-Za-z]\.\s*[A-Za-z]+)', text),
        'vin':          vins[0] if vins else None,
    }

def _irp(text):
    vins = VIN_RE.findall(text)
    yr   = re.search(r'KS\s+(\d{4})', text)
    return {
        'truck_unit': _first(r'UNIT\s*[#\s]*(\d+)', text),
        'vin':        vins[0] if vins else None,
        'plate_no':   _first(r'LICENSE PLATE NO\.\s+([A-Z0-9\-]+)', text),
        'year':       int(yr.group(1)) if yr else None,
    }

def _title(text):
    vins  = VIN_RE.findall(text)
    dates = DATE_RE.findall(text)
    makes = ['Peterbilt','Kenworth','Freightliner','International','Volvo','Mack','Western Star']
    yr_mk = re.search(r'(\d{4})\s+(' + '|'.join(makes) + ')', text)
    model = _first(r'(?:' + '|'.join(makes) + r')\s+([A-Z0-9]+)', text)
    odo   = _first(r'ODOMETER[^\d]*([\d,]+)', text)
    return {
        'vin':      vins[0] if vins else None,
        'title_no': _first(r'TITLE NUMBER\s+([A-Z0-9]+)', text),
        'date':     _parse_date(dates[0]) if dates else None,
        'year':     int(yr_mk.group(1)) if yr_mk else None,
        'make':     yr_mk.group(2) if yr_mk else None,
        'model':    model,
        'color':    _first(r'COLOR\s+([A-Za-z]+)\s', text),
        'odometer': int(odo.replace(',','')) if odo else None,
    }

def _ifta(text):
    dates = DATE_RE.findall(text)
    gals  = re.findall(r'([\d,]+\.?\d*)\s*(?:gal|GAL)', text)
    tax   = _first(r'TOTAL TAX DUE\s+\$([\d,]+\.?\d{0,2})', text) or \
            _first(r'Tax Due\s+\$([\d,]+\.?\d{0,2})', text)
    return {
        'doc_number':   _first(r'IFTA ACCOUNT NO\.\s+([A-Z0-9\-]+)', text),
        'date':         _parse_date(dates[0]) if dates else None,
        'amount_total': _amt(tax),
        'vendor':       'Kansas DOR - IFTA',
        'category':     'IFTA Fuel Tax',
    }

def _form2290(text):
    vins  = VIN_RE.findall(text)
    dates = DATE_RE.findall(text)
    tax   = _first(r'Total tax\s+\$([\d,]+\.?\d{0,2})', text) or \
            _first(r'Amount due\s+\$([\d,]+\.?\d{0,2})', text)
    return {
        'vin':          vins[0] if vins else None,
        'date':         _parse_date(dates[0]) if dates else None,
        'amount_total': _amt(tax),
        'vendor':       'IRS',
        'category':     'Federal HVUT (Form 2290)',
    }

def _lease(text):
    vins  = VIN_RE.findall(text)
    dates = DATE_RE.findall(text)
    amts  = re.findall(r'\$([\d,]+\.?\d{0,2})', text)
    return {
        'truck_unit': _first(r'Fleet Unit No\.\s*(\d+)', text),
        'doc_number': _first(r'Lease No\.\s+([A-Z0-9\-]+)', text),
        'date':       _parse_date(dates[0]) if dates else None,
        'amount_total': _amt(amts[0]) if amts else None,
        'vin':        vins[0] if vins else None,
        'category':   'Equipment Lease',
    }

HANDLERS = {
    'bill_of_sale_purchase': _bill_of_sale,
    'bill_of_sale_sale':     _bill_of_sale,
    'cdl':                   _cdl,
    'insurance':             _insurance,
    'maintenance_invoice':   _invoice,
    'irp_card':              _irp,
    'certificate_of_title':  _title,
    'ifta_return':           _ifta,
    'form_2290':             _form2290,
    'lease_agreement':       _lease,
}

def extract_entities(filename: str, raw_text: str) -> dict:
    doc_type = _classify(raw_text)
    base = {'doc_type': doc_type}
    if doc_type in HANDLERS:
        base.update(HANDLERS[doc_type](raw_text))
    return base
