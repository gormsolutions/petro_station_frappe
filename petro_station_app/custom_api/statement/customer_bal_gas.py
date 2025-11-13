import frappe
import hashlib
import json

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
    customer_section="Gas Customer"  # default section
):
    """
    Fast customer outstanding summary using GL Entry
    - Caches page results + counts for 5 minutes
    - Provides recordsTotal and recordsFiltered for DataTables
    """

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


@frappe.whitelist()
def get_customer_outstanding_summary(company=None, from_date=None, to_date=None):
    """
    Returns aggregated summary for dashboards:
    - total balance
    - positive vs negative
    - top customers
    """
    filters = ["gle.party_type='Customer'"]
    args = []

    if company:
        filters.append("gle.company=%s")
        args.append(company)
    if from_date and to_date:
        filters.append("gle.posting_date BETWEEN %s AND %s")
        args.extend([from_date, to_date])

    where_clause = " AND ".join(filters)

    # Total balance and split positive/negative
    total_sql = f"""
        SELECT
            SUM(gle.debit - gle.credit) AS total_balance,
            SUM(CASE WHEN gle.debit - gle.credit > 0 THEN gle.debit - gle.credit ELSE 0 END) AS positive,
            SUM(CASE WHEN gle.debit - gle.credit < 0 THEN gle.debit - gle.credit ELSE 0 END) AS negative
        FROM `tabGL Entry` gle
        LEFT JOIN `tabCustomer` c ON gle.party=c.name
        WHERE {where_clause}
    """
    total_data = frappe.db.sql(total_sql, tuple(args), as_dict=True)[0]

    # Top 10 customers
    top_sql = f"""
        SELECT
            gle.party AS customer,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        LEFT JOIN `tabCustomer` c ON gle.party=c.name
        WHERE {where_clause}
        GROUP BY gle.party
        ORDER BY balance DESC
        LIMIT 10
    """
    top_customers = frappe.db.sql(top_sql, tuple(args), as_dict=True)
    
    # Map customer names
    parties = [d["customer"] for d in top_customers]
    name_map = {}
    if parties:
        for d in frappe.db.get_all("Customer",
                                   filters={"name": ["in", parties]},
                                   fields=["name", "customer_name"]):
            name_map[d["name"]] = d["customer_name"]
    for row in top_customers:
        row["customer_name"] = name_map.get(row["customer"], row["customer"])

    return {
        "summary": total_data,
        "top_customers": top_customers
    }
