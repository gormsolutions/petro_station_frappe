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
