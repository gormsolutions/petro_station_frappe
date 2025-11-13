import frappe

@frappe.whitelist()
def get_party_outstandings_with_items_and_company(from_date=None, to_date=None, cost_center=None, company=None):
    """
    Fetch outstanding balances for customers and suppliers, grouped by party, including invoice details with items.
    """
    
    # Fetch outstanding balances for Customers (No Filters)
    customer_entries = frappe.db.sql("""
        SELECT 
            gle.party AS party_name,
            'Customer' AS party_type,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Customer'
        GROUP BY gle.party
    """, as_dict=True)

    # Fetch outstanding balances for Suppliers (No Filters)
    supplier_entries = frappe.db.sql("""
        SELECT 
            gle.party AS party_name,
            'Supplier' AS party_type,
            SUM(gle.credit - gle.debit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Supplier'
        GROUP BY gle.party
    """, as_dict=True)

    # Prepare conditions and filters for invoices
    conditions = "si.docstatus = 1 AND si.outstanding_amount > 0"
    supplier_conditions = "pi.docstatus = 1 AND pi.outstanding_amount > 0"
    filters = []

    if from_date and to_date:
        conditions += " AND si.posting_date BETWEEN %s AND %s"
        supplier_conditions += " AND pi.posting_date BETWEEN %s AND %s"
        filters.extend([from_date, to_date])
    
    if company:
        conditions += " AND si.company = %s"
        supplier_conditions += " AND pi.company = %s"
        filters.append(company)

    # Fetch outstanding customer invoices
    customer_invoices = frappe.db.sql(f"""
        SELECT 
            si.customer AS party_name,
            si.name AS invoice_no,
            si.posting_date,
            si.outstanding_amount
        FROM `tabSales Invoice` si
        WHERE {conditions}
    """, tuple(filters), as_dict=True)

    # Fetch outstanding supplier invoices
    supplier_invoices = frappe.db.sql(f"""
        SELECT 
            pi.supplier AS party_name,
            pi.name AS invoice_no,
            pi.posting_date,
            pi.outstanding_amount
        FROM `tabPurchase Invoice` pi
        WHERE {supplier_conditions}
    """, tuple(filters), as_dict=True)

    # Fetch Sales Invoice Items
    customer_items = frappe.db.sql("""
        SELECT 
            sii.parent AS invoice_no,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate
        FROM `tabSales Invoice Item` sii
    """, as_dict=True)

    # Fetch Purchase Invoice Items
    supplier_items = frappe.db.sql("""
        SELECT 
            pii.parent AS invoice_no,
            pii.item_code,
            pii.item_name,
            pii.qty,
            pii.rate
        FROM `tabPurchase Invoice Item` pii
    """, as_dict=True)

    # Organize invoices with their items
    customer_invoice_map = {inv["invoice_no"]: inv for inv in customer_invoices}
    supplier_invoice_map = {inv["invoice_no"]: inv for inv in supplier_invoices}

    for item in customer_items:
        if item["invoice_no"] in customer_invoice_map:
            customer_invoice_map[item["invoice_no"]].setdefault("items", []).append(item)

    for item in supplier_items:
        if item["invoice_no"] in supplier_invoice_map:
            supplier_invoice_map[item["invoice_no"]].setdefault("items", []).append(item)

    # Enrich results with customer and supplier names
    customers = []
    for entry in customer_entries:
        customer_name = frappe.db.get_value("Customer", entry["party_name"], "customer_name")
        customer_data = {
            "party_name": entry["party_name"],
            "party_type": "Customer",
            "balance": entry["balance"],
            "customer_name": customer_name,
            "invoices": [customer_invoice_map[inv] for inv in customer_invoice_map if customer_invoice_map[inv]["party_name"] == entry["party_name"]]
        }
        customers.append(customer_data)

    suppliers = []
    for entry in supplier_entries:
        supplier_name = frappe.db.get_value("Supplier", entry["party_name"], "supplier_name")
        supplier_data = {
            "party_name": entry["party_name"],
            "party_type": "Supplier",
            "balance": entry["balance"],
            "supplier_name": supplier_name,
            "invoices": [supplier_invoice_map[inv] for inv in supplier_invoice_map if supplier_invoice_map[inv]["party_name"] == entry["party_name"]]
        }
        suppliers.append(supplier_data)

    return {
        "customers": customers,
        "suppliers": suppliers
    }


import frappe
import hashlib
import json
from datetime import date

def _cache_key(prefix: str, params: dict) -> str:
    """Stable, compact cache key"""
    payload = json.dumps(params, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(payload.encode()).hexdigest()}"

def _sql_results(sql, args):
    return frappe.db.sql(sql, args, as_dict=True)

@frappe.whitelist()
def get_customer_outstandings(
    from_date=None,
    to_date=None,
    company=None,
    search=None,
    limit_start=0,
    limit_page_length=20,
    customer_section="ANNEX/ELGON"  # default section
):
    """
    Fast customer outstanding summary using GL Entry
    - Caches page results + counts for 5 minutes
    - Provides recordsTotal and recordsFiltered for DataTables
    """

     # Default date range
    if not from_date:
        from_date = "2024-08-01"
    if not to_date:
        to_date = date.today().strftime("%Y-%m-%d")

    # sanitize limits
    try:
        limit_start = int(limit_start or 0)
    except Exception:
        limit_start = 0
    try:
        limit_page_length = min(int(limit_page_length or 20), 5000)
    except Exception:
        limit_page_length = 20

    ledger_table = "tabGL Entry"

    # Build WHERE conditions
    base_conditions = [
        "gle.party_type = 'Customer'",
        "c.custom_customer_section = %s"
    ]
    base_filters = [customer_section]

    if from_date and to_date:
        base_conditions.append("gle.posting_date BETWEEN %s AND %s")
        base_filters.extend([from_date, to_date])

    if company:
        base_conditions.append("gle.company = %s")
        base_filters.append(company)

    # Optional search
    search_condition = ""
    search_filters = []
    if search:
        search_condition = " AND (gle.party LIKE %s OR c.customer_name LIKE %s)"
        search_filters = [f"{search}%", f"{search}%"]

    where_base = " AND ".join(base_conditions)
    where_with_search = where_base + search_condition

    # Main page query (filtered)
    page_sql = f"""
        SELECT
            gle.party AS party_name,
            SUM(gle.debit - gle.credit) AS balance
        FROM `{ledger_table}` gle
        LEFT JOIN `tabCustomer` c ON gle.party = c.name
        WHERE {where_with_search}
        GROUP BY gle.party
        HAVING SUM(gle.debit - gle.credit) != 0
        ORDER BY balance DESC
        LIMIT %s OFFSET %s
    """
    page_args = tuple(base_filters + search_filters + [limit_page_length, limit_start])

    # Count filtered
    count_filtered_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT gle.party
            FROM `{ledger_table}` gle
            LEFT JOIN `tabCustomer` c ON gle.party = c.name
            WHERE {where_with_search}
            GROUP BY gle.party
            HAVING SUM(gle.debit - gle.credit) != 0
        ) x
    """
    count_filtered_args = tuple(base_filters + search_filters)

    # Count total (no search)
    count_total_sql = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT gle.party
            FROM `{ledger_table}` gle
            LEFT JOIN `tabCustomer` c ON gle.party = c.name
            WHERE {where_base}
            GROUP BY gle.party
            HAVING SUM(gle.debit - gle.credit) != 0
        ) x
    """
    count_total_args = tuple(base_filters)

    # Caching (5 minutes)
    cache = frappe.cache()

    page_key = _cache_key("cust_out_page", {
        "from": from_date, "to": to_date, "company": company,
        "search": search, "start": limit_start, "len": limit_page_length,
        "section": customer_section
    })
    filt_key = _cache_key("cust_out_count_filtered", {
        "from": from_date, "to": to_date, "company": company,
        "search": search, "section": customer_section
    })
    total_key = _cache_key("cust_out_count_total", {
        "from": from_date, "to": to_date, "company": company,
        "section": customer_section
    })

    customers = cache.get_value(page_key)
    if customers is None:
        customers = _sql_results(page_sql, page_args)
        cache.set_value(page_key, customers, expires_in_sec=300)

    # Map to customer_name for pretty display
    parties = [d["party_name"] for d in customers]
    name_map = {}
    if parties:
        for d in frappe.db.get_all(
            "Customer",
            filters={"name": ["in", parties]},
            fields=["name", "customer_name"]
        ):
            name_map[d["name"]] = d["customer_name"]
    for row in customers:
        row["customer_name"] = name_map.get(row["party_name"], row["party_name"])

    # counts
    records_filtered = cache.get_value(filt_key)
    if records_filtered is None:
        res = _sql_results(count_filtered_sql, count_filtered_args)
        records_filtered = (res[0]["total"] if res else 0) or 0
        cache.set_value(filt_key, records_filtered, expires_in_sec=300)

    records_total = cache.get_value(total_key)
    if records_total is None:
        res = _sql_results(count_total_sql, count_total_args)
        records_total = (res[0]["total"] if res else 0) or 0
        cache.set_value(total_key, records_total, expires_in_sec=300)

    return {
        "customers": customers,
        "recordsTotal": records_total,       # e.g. 378 (no search)
        "recordsFiltered": records_filtered  # e.g. 320 (with search)
    }
