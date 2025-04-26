import frappe

@frappe.whitelist()
def execute(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    from_date = filters.get("from_date")
    to_date   = filters.get("to_date")
    if not from_date or not to_date:
        frappe.throw("Please select both From Date and To Date")

    items = ["PMS", "AGO", "V Power", "BIK"]
    default_currency = frappe.db.get_single_value("Global Defaults", "default_currency")
    data = []

    for item in items:
        opening_qty, opening_amount     = get_stock_balance(item, from_date)
        closing_qty, closing_amount     = get_stock_balance(item, to_date)
        purchases_qty, purchases_amount = get_purchases(item, from_date, to_date)

        cogs_amount = opening_amount + purchases_amount - closing_amount

        data.append({
            "item": item,
            "opening_qty": opening_qty,
            "opening_amount": opening_amount,
            "purchases_qty": purchases_qty,
            "purchases_amount": purchases_amount,
            "closing_qty": closing_qty,
            "closing_amount": closing_amount,
            "cogs_amount": cogs_amount,
            "currency": default_currency
        })

    columns = [
        {"label": "Item",              "fieldname": "item",              "fieldtype": "Data",      "width": 120},
        {"label": "Opening Qty",      "fieldname": "opening_qty",      "fieldtype": "Float",     "width": 100},
        {"label": "Opening Amount",   "fieldname": "opening_amount",   "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": "Purchases Qty",    "fieldname": "purchases_qty",    "fieldtype": "Float",     "width": 100},
        {"label": "Purchases Amount", "fieldname": "purchases_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": "Closing Qty",      "fieldname": "closing_qty",      "fieldtype": "Float",     "width": 100},
        {"label": "Closing Amount",   "fieldname": "closing_amount",   "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": "COGS Amount",      "fieldname": "cogs_amount",      "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": "Currency",         "fieldname": "currency",         "fieldtype": "Data",      "width":  80},
    ]

    daily_sales_html = get_daily_sales(from_date, to_date)

    return {"columns": columns, "result": data, "daily_sales_html": daily_sales_html}


def get_stock_balance(item_code, date):
    stock = frappe.db.sql("""
        SELECT
            SUM(actual_qty) as total_qty,
            SUM(valuation_rate * actual_qty) as total_amount
        FROM `tabStock Ledger Entry`
        WHERE item_code=%s AND posting_date<=%s
    """, (item_code, date), as_list=True)
    return stock[0][0] or 0, stock[0][1] or 0


def get_purchases(item_code, from_date, to_date):
    purchases = frappe.db.sql("""
        SELECT
            SUM(actual_qty) as total_qty,
            SUM(valuation_rate * actual_qty) as total_amount
        FROM `tabStock Ledger Entry`
        WHERE item_code=%s
          AND posting_date BETWEEN %s AND %s
          AND voucher_type IN ('Purchase Receipt','Stock Entry')
    """, (item_code, from_date, to_date), as_list=True)
    return purchases[0][0] or 0, purchases[0][1] or 0

def get_daily_sales(from_date, to_date):
    # Get unique from_dates within the selected range for submitted documents
    dates = frappe.db.sql("""
        SELECT DISTINCT from_date
        FROM `tabStation Shift Management`
        WHERE from_date BETWEEN %s AND %s
          AND docstatus = 1
        ORDER BY from_date ASC
    """, (from_date, to_date), as_list=True)

    date_list = [d[0].strftime("%d/%m/%Y") for d in dates]
    if not date_list:
        return "<p>No sales data available for the selected period.</p>"

    # Get unique pump_or_tank items sold during this period, considering only submitted documents
    pumps = frappe.db.sql("""
        SELECT DISTINCT sii.pump_or_tank
        FROM `tabStation Shift Management` ssm
        JOIN `tabStation Shift Management item` sii ON sii.parent = ssm.name
        WHERE ssm.from_date BETWEEN %s AND %s
          AND ssm.docstatus = 1
        ORDER BY sii.pump_or_tank
    """, (from_date, to_date), as_list=True)

    pump_list = [p[0] for p in pumps]

    # Build table header
    html = """<table border="1" cellpadding="5" cellspacing="0"
        style="border-collapse: collapse; text-align: center; font-family: Arial; margin-top:20px;">
        <thead>
            <tr>
                <th style="color: red; font-style: italic;">Pump / Tank</th>
                <th style="color: red; font-style: italic;">Unit</th>"""
    for date in date_list:
        html += f'<th colspan="3" style="color: blue;">{date}</th>'
    html += '<th rowspan="2" style="color: purple;">Total Sold</th></tr>'

    # second header row for Opening / Closing / Sold
    html += '<tr><th></th><th></th>'
    for _ in date_list:
        html += (
            '<th style="color: green;">Opening</th>'
            '<th style="color: green;">Closing</th>'
            '<th style="color: green;">Sold</th>'
        )
    html += '</tr></thead><tbody>'

    # Build each pump row
    for pump in pump_list:
        row = f'<tr><td><b>{pump}</b></td><td style="color: green;">Litres</td>'
        total_sold = 0.0

        for date in dates:
            day = date[0]
            readings = frappe.db.sql("""
                SELECT 
                    SUM(sii.opening_meter_reading),
                    SUM(sii.closing_meter_reading),
                    SUM(sii.closing_meter_reading - sii.opening_meter_reading)
                FROM `tabStation Shift Management` ssm
                JOIN `tabStation Shift Management item` sii 
                  ON sii.parent = ssm.name
                WHERE ssm.from_date = %s
                  AND sii.pump_or_tank = %s
                  AND ssm.docstatus = 1
            """, (day, pump), as_list=True)[0]

            opening, closing, sold = (readings[0] or 0), (readings[1] or 0), (readings[2] or 0)
            total_sold += sold

            row += (
                f'<td>{opening:,.2f}</td>'
                f'<td>{closing:,.2f}</td>'
                f'<td>{sold:,.2f}</td>'
            )

        # Append grand total sold for this pump
        row += f'<td style="font-weight:bold; color: purple;">{total_sold:,.2f}</td>'
        row += '</tr>'

        html += row

    html += '</tbody></table>'
    return html
