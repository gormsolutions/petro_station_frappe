import frappe

@frappe.whitelist()
def get_party_outstandings_with_items_and_company(from_date=None, to_date=None, cost_center=None, company=None):
    """
    Fetch outstanding balances for both customers and suppliers, grouped by customer and supplier,
    including the specific items taken, the related invoices associated with the outstanding balance,
    and the rate for each item. Filters by company, date range, and cost center.
    """

    # Validate input parameters
    # if not from_date or not to_date:
    #     frappe.throw("Both 'from_date' and 'to_date' are required.")

    # Prepare filters
    conditions = "gle.docstatus = 1"
    filters = []

    # Add date range filter
    if from_date and to_date:
        conditions += " AND gle.posting_date BETWEEN %s AND %s"
        filters.extend([from_date, to_date])

    # Add cost center filter if provided
    if cost_center:
        conditions += " AND gle.cost_center = %s"
        filters.append(cost_center)

    # Add company filter if provided
    if company:
        conditions += " AND gle.company = %s"
        filters.append(company)

    # Filter by specific accounts (suppliers and customers)
    account_filter = "gle.account IN ('2110 - Creditors - SE', '1310 - Debtors - SE')"
    conditions += f" AND {account_filter}"

    # Fetch customer outstandings, group by customer
    customer_entries = frappe.db.sql(f"""
        SELECT 
            gle.party AS party_name,
            gle.party_type,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Customer' AND {conditions}
        GROUP BY gle.party
        HAVING balance > 0
    """, tuple(filters), as_dict=True)

    # Fetch supplier outstandings, group by supplier
    supplier_entries = frappe.db.sql(f"""
        SELECT 
            gle.party AS party_name,
            gle.party_type,
            SUM(gle.credit - gle.debit) AS balance
        FROM `tabGL Entry` gle
        WHERE gle.party_type = 'Supplier' AND {conditions}
        GROUP BY gle.party
        HAVING balance > 0
    """, tuple(filters), as_dict=True)

    # Fetch customer invoice details (including items and rate)
    customer_invoices = frappe.db.sql(f"""
        SELECT 
            gle.party AS party_name,
            gle.voucher_no AS invoice_no,
            gle.posting_date,
            gle.debit - gle.credit AS outstanding_amount,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate
        FROM `tabGL Entry` gle
        JOIN `tabSales Invoice Item` sii ON gle.voucher_no = sii.parent
        WHERE gle.party_type = 'Customer' AND {conditions} AND gle.debit - gle.credit > 0
    """, tuple(filters), as_dict=True)

    # Fetch supplier invoice details (including items and rate)
    supplier_invoices = frappe.db.sql(f"""
        SELECT 
            gle.party AS party_name,
            gle.voucher_no AS invoice_no,
            gle.posting_date,
            gle.credit - gle.debit AS outstanding_amount,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate
        FROM `tabGL Entry` gle
        JOIN `tabPurchase Invoice Item` sii ON gle.voucher_no = sii.parent
        WHERE gle.party_type = 'Supplier' AND {conditions} AND gle.credit - gle.debit > 0
    """, tuple(filters), as_dict=True)

    # Enrich results with customer and supplier names
    customers = []
    for entry in customer_entries:
        customer_name = frappe.db.get_value("Customer", {"name": entry["party_name"]}, "customer_name")
        customer_data = {
            "party_name": entry["party_name"],
            "party_type": entry["party_type"],
            "balance": entry["balance"],
            "customer_name": customer_name,
            "invoices": []
        }

        # Add invoice details for the customer
        for invoice in customer_invoices:
            if invoice["party_name"] == entry["party_name"]:
                invoice_data = {
                    "invoice_no": invoice["invoice_no"],
                    "posting_date": invoice["posting_date"],
                    "outstanding_amount": invoice["outstanding_amount"],
                    "items": []
                }
                # Add items associated with the invoice
                invoice_data["items"].append({
                    "item_code": invoice["item_code"],
                    "item_name": invoice["item_name"],
                    "quantity": invoice["qty"],
                    "rate": invoice["rate"]
                })
                customer_data["invoices"].append(invoice_data)
        
        customers.append(customer_data)

    suppliers = []
    for entry in supplier_entries:
        supplier_name = frappe.db.get_value("Supplier", {"name": entry["party_name"]}, "supplier_name")
        supplier_data = {
            "party_name": entry["party_name"],
            "party_type": entry["party_type"],
            "balance": entry["balance"],
            "supplier_name": supplier_name,
            "invoices": []
        }

        # Add invoice details for the supplier
        for invoice in supplier_invoices:
            if invoice["party_name"] == entry["party_name"]:
                invoice_data = {
                    "invoice_no": invoice["invoice_no"],
                    "posting_date": invoice["posting_date"],
                    "outstanding_amount": invoice["outstanding_amount"],
                    "items": []
                }
                # Add items associated with the invoice
                invoice_data["items"].append({
                    "item_code": invoice["item_code"],
                    "item_name": invoice["item_name"],
                    "quantity": invoice["qty"],
                    "rate": invoice["rate"]
                })
                supplier_data["invoices"].append(invoice_data)
        
        suppliers.append(supplier_data)

    # Combine results
    return {
        "customers": customers,
        "suppliers": suppliers
    }
