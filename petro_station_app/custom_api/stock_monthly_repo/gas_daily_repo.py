import frappe

@frappe.whitelist()
def get_stock_ledger_entries(start_date, end_date, user=None):
    # Get all warehouses linked to the user
    warehouse_records = frappe.get_all(
        "Warehouse",
        filters={"custom_user": user},
        fields=["name"]
    )

    # Extract warehouse names into a list
    warehouses = [w["name"] for w in warehouse_records]

    # If no warehouses found, return an empty list
    if not warehouses:
        return []

    # Get stock ledger entries
    stock_ledger_entries = frappe.get_all(
        "Stock Ledger Entry",
        filters={
            "voucher_type": "Sales Invoice",
            "posting_date": ["between", [start_date, end_date]],
            "warehouse": ["in", warehouses]
        },
        fields=["voucher_no", "posting_date", "actual_qty", "item_code", "warehouse"]
    )

    item_qty_map = {}

    # Separate paid and unpaid totals for each warehouse and item
    total_paid_qty = {}
    total_unpaid_qty = {}

    for entry in stock_ledger_entries:
        # Fetch packed items with 'EMPTY' in item_code
        packed_items = frappe.get_all(
            "Packed Item",
            filters={"parent": entry["voucher_no"], "item_code": ["like", "%EMPTY%"]},
            fields=["item_code"]
        )

        # Create a set of packed item codes
        packed_item_codes = {item["item_code"] for item in packed_items}

        # Exclude packed items
        if entry["item_code"] not in packed_item_codes:
            key = f"{entry['item_code']}|{entry['warehouse']}"  # Create a string key
            
            # Fetch payment status from Sales Invoice
            payment_status = frappe.get_value("Sales Invoice", entry["voucher_no"], "status")

            if key in item_qty_map:
                item_qty_map[key]["qty_change"] += entry["actual_qty"]
            else:
                item_qty_map[key] = {
                    "item_code": entry["item_code"],
                    "warehouse": entry["warehouse"],
                    "qty_change": entry["actual_qty"],
                    "posting_date": entry["posting_date"],  # Keeping one posting date
                    "payment_status": payment_status,  # Add payment status
                }

            # Separate totals based on payment status
            if payment_status == "Paid":
                if key not in total_paid_qty:
                    total_paid_qty[key] = 0
                total_paid_qty[key] += entry["actual_qty"]
            else:
                if key not in total_unpaid_qty:
                    total_unpaid_qty[key] = 0
                total_unpaid_qty[key] += entry["actual_qty"]

    # Ensure all keys are converted to strings in the final return response
    response_data = {
        "entries": [
            {**entry, "key": str(entry["item_code"]) + "|" + str(entry["warehouse"])} 
            for entry in item_qty_map.values()
        ],
        "total_paid_qty": {str(key): value for key, value in total_paid_qty.items()},
        "total_unpaid_qty": {str(key): value for key, value in total_unpaid_qty.items()},
    }

    return response_data


@frappe.whitelist()
def get_items_from_sales_and_purchase_by_group(cost_center=None, warehouse=None, start_date=None, end_date=None, item_group_filter=None):
    # Initialize an empty dictionary to store grouped results by Item Group
    grouped_data = {}

    # Filter conditions for purchase and sales invoices
    purchase_filter_conditions = ""
    sales_filter_conditions = ""

    if warehouse:
        purchase_filter_conditions += f" AND pii.warehouse = '{warehouse}'"
        sales_filter_conditions += f" AND sii.warehouse = '{warehouse}'"

    if cost_center:
        purchase_filter_conditions += f" AND pii.cost_center = '{cost_center}'"
        sales_filter_conditions += f" AND sii.cost_center = '{cost_center}'"

    if start_date and end_date:
        purchase_filter_conditions += f" AND pi.posting_date BETWEEN '{start_date}' AND '{end_date}'"
        sales_filter_conditions += f" AND si.posting_date BETWEEN '{start_date}' AND '{end_date}'"
    elif start_date:
        purchase_filter_conditions += f" AND pi.posting_date >= '{start_date}'"
        sales_filter_conditions += f" AND si.posting_date >= '{start_date}'"
    elif end_date:
        purchase_filter_conditions += f" AND pi.posting_date <= '{end_date}'"
        sales_filter_conditions += f" AND si.posting_date <= '{end_date}'"

    # Fetch all Sales Invoice items and their average rates
    sales_data = frappe.db.sql("""
        SELECT
            sii.item_code,
            AVG(sii.rate) AS average_rate,
            i.item_group
        FROM
            `tabSales Invoice` si
            INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.name
        WHERE
            si.docstatus = 1  # Only submitted invoices
            {conditions}
        GROUP BY sii.item_code, i.item_group
    """.format(conditions=sales_filter_conditions), as_dict=True)

    # Filter the sales data by item group if provided
    if item_group_filter:
        sales_data = [sale for sale in sales_data if sale['item_group'] == item_group_filter]

    # Fetch purchase details from Purchase Invoice Items
    purchase_data = frappe.db.sql("""
        SELECT
            pii.item_code,
            pii.warehouse,
            pii.qty,
            pii.rate,
            i.item_group
        FROM
            `tabPurchase Invoice` pi
            INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            INNER JOIN `tabItem` i ON pii.item_code = i.name
        WHERE
            pi.docstatus = 1  # Only submitted invoices
            {conditions}
    """.format(conditions=purchase_filter_conditions), as_dict=True)

    # Filter purchase data by item group if provided
    if item_group_filter:
        purchase_data = [purchase for purchase in purchase_data if purchase['item_group'] == item_group_filter]

    # Group purchase details by item_code
    purchase_details_grouped = {}
    for purchase in purchase_data:
        if purchase['item_code'] not in purchase_details_grouped:
            purchase_details_grouped[purchase['item_code']] = []
        purchase_details_grouped[purchase['item_code']].append({
            'warehouse': purchase['warehouse'],
            'qty': purchase['qty'],
            'rate': purchase['rate']
        })

    # Create a dictionary to store the final grouped data by Item Group
    for sale in sales_data:
        item_code = sale['item_code']
        item_group = sale['item_group']
        average_sales_rate = sale['average_rate']

        # Initialize the item group if not already in the grouped_data dictionary
        if item_group not in grouped_data:
            grouped_data[item_group] = []

        # Add the purchase and sales data for each item
        grouped_data[item_group].append({
            "item_code": item_code,
            "average_sales_rate": average_sales_rate,
            "purchase_details": purchase_details_grouped.get(item_code, [])
        })

    return grouped_data


import frappe

@frappe.whitelist()
def get_average_selling_price_by_filters(user=None, start_date=None, end_date=None):
    # Get all warehouses linked to the user if a user is provided
    if user:
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"custom_user": user},
            pluck="name"
        )
    else:
        # If no user is provided, get all warehouses
        warehouses = frappe.get_all(
            "Warehouse",
            pluck="name"
        )

    # Base SQL Query
    query = """
        SELECT
            sii.item_code,
            i.item_group,
            ROUND(AVG(sii.rate), 3) AS average_sales_rate,
            CASE 
                WHEN i.item_group = 'Fuel' THEN sii.warehouse
                ELSE NULL
            END AS warehouse
        FROM
            `tabSales Invoice` si
            INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.item_code
        WHERE
            si.docstatus = 1
    """

    # Query Parameters
    params = {}

    # Apply Warehouse Filter if warehouses are provided
    if warehouses:
        query += " AND sii.warehouse IN %(warehouses)s"
        params["warehouses"] = tuple(warehouses)

    # Apply Date Filters if provided
    if start_date:
        query += " AND si.posting_date >= %(start_date)s"
        params["start_date"] = start_date
    if end_date:
        query += " AND si.posting_date <= %(end_date)s"
        params["end_date"] = end_date

    # Adjust GROUP BY clause
    query += " GROUP BY sii.item_code, i.item_group, warehouse"

    # Execute Query
    result = frappe.db.sql(query, params, as_dict=True)

    return result


@frappe.whitelist()
def get_purchase_invoices(cost_center, start_date, end_date):
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "cost_center": cost_center,
            "posting_date": ["between", [start_date, end_date]],
            "docstatus": ["!=", 2]  # Exclude cancelled invoices
        },
        fields=["name", "cost_center", "supplier", "posting_date", "grand_total", "outstanding_amount"],
    )
    
    for invoice in invoices:
        invoice["items"] = frappe.get_all(
            "Purchase Invoice Item",
            filters={"parent": invoice["name"]},
            fields=["item_code", "qty", "rate", "amount"],
        )
    
    return invoices
