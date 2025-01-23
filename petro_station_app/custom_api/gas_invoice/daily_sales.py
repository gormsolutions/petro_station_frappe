# import frappe
# from frappe.utils import today
# from datetime import datetime

# @frappe.whitelist()
# def fetch_invoices_and_stock_entries(start_date, end_date, warehouse, cost_center=None):
#     # Convert start_date and end_date to datetime.date objects for comparison
#     start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
#     end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

#     # Base SQL query to fetch sales invoices
#     query = """
#         SELECT 
#             si.name AS invoice_name, 
#             si.posting_date, 
#             si.status,
#             si.customer, 
#             si.grand_total,
#             si.outstanding_amount,  # Fetch the outstanding amount for each invoice
#             sii.item_code,
#             sii.item_name,
#             sii.qty,
#             sii.rate,
#             sii.warehouse,
#             sii.cost_center  # Fetch the cost center for the item
#         FROM 
#             `tabSales Invoice` si
#         LEFT JOIN 
#             `tabSales Invoice Item` sii ON si.name = sii.parent
#         WHERE 
#             si.docstatus = 1
#             AND si.posting_date BETWEEN %s AND %s
#             AND sii.warehouse = %s
#     """

#     # Add the cost_center filter to the query if it's provided
#     if cost_center:
#         query += " AND sii.cost_center = %s"
#         params = (start_date, end_date, warehouse, cost_center)
#     else:
#         params = (start_date, end_date, warehouse)

#     # Fetch the sales invoices with the optional cost_center filter
#     sales_invoices = frappe.db.sql(query, params, as_dict=True)

#     # Dictionary to hold grouped invoice data
#     grouped_invoices = {}
#     grand_total_range = 0  # To accumulate the grand total for the filtered range
#     unpaid_total_range = 0  # To accumulate the unpaid total for the filtered range
#     outstanding_total_range = 0  # To accumulate the outstanding total for the filtered range

#     for invoice in sales_invoices:
#         invoice_name = invoice['invoice_name']
        
#         if invoice_name not in grouped_invoices:
#             grouped_invoices[invoice_name] = {
#                 'invoice_name': invoice_name,
#                 'posting_date': invoice['posting_date'],
#                 'status': invoice['status'],
#                 'customer': invoice['customer'],
#                 'grand_total': invoice['grand_total'],  # Set grand_total only when the invoice is first encountered
#                 'items': [],
#                 'opening_stock': 0,
#                 'closing_stock': 0,
#                 'outstanding_amount': invoice['outstanding_amount'],  # Initialize outstanding amount
#                 'unpaid_amount': invoice['outstanding_amount'] if invoice['outstanding_amount'] > 0 else 0,  # Initialize unpaid amount
#             }
#             grand_total_range += invoice['grand_total']  # Add to total only once
#             outstanding_total_range += invoice['outstanding_amount']  # Add to outstanding total only once
#             if invoice['outstanding_amount'] > 0:
#                 unpaid_total_range += invoice['outstanding_amount']  # Add to unpaid total only once

#         item_code = invoice['item_code']

#         # Fetch the opening stock (last stock entry before the start_date)
#         opening_stock = frappe.db.sql(""" 
#             SELECT sle.`qty_after_transaction` AS opening_stock 
#             FROM `tabStock Ledger Entry` sle 
#             WHERE sle.item_code = %s 
#                 AND sle.warehouse = %s
#                 AND sle.posting_datetime < %s
#             ORDER BY sle.posting_datetime DESC
#             LIMIT 1
#         """, (item_code, warehouse, start_date), as_dict=True)

#         opening_stock = opening_stock[0].get('opening_stock', 0) if opening_stock else 0

#         # Sum the actual_qty from Stock Ledger Entries (for the same item and within the filtered date range)
#         total_qty_sold = sum(
#             sle['actual_qty'] for sle in frappe.db.sql("""
#                 SELECT actual_qty
#                 FROM `tabStock Ledger Entry` sle
#                 WHERE sle.item_code = %s 
#                     AND sle.warehouse = %s
#                     AND DATE(sle.posting_datetime) BETWEEN %s AND %s
#             """, (item_code, warehouse, start_date, end_date), as_dict=True)
#         )

#         # Calculate the closing stock (subtract the total actual_qty sold from the opening stock)
#         closing_stock = opening_stock + total_qty_sold

#         # Add item data to the grouped invoice
#         grouped_invoices[invoice_name]['items'].append({
#             'item_code': item_code,
#             'item_name': invoice['item_name'],
#             'si_qty': invoice['qty'],
#             'stock_qty': total_qty_sold,  # Summed quantity from the stock ledger entries
#             'rate': invoice['rate'],
#             'warehouse': invoice['warehouse'],
#             'cost_center': invoice['cost_center'],  # Add cost center to the item data
#             'opening_stock': opening_stock,
#             'closing_stock': closing_stock
#         })

#         # Accumulate the opening and closing stock for the entire invoice
#         grouped_invoices[invoice_name]['opening_stock'] += opening_stock
#         grouped_invoices[invoice_name]['closing_stock'] += closing_stock

#     # Convert the dictionary to a list and return it along with grand_total_range, unpaid_total_range, and outstanding_total_range
#     return {
#         'grouped_invoices': list(grouped_invoices.values()),
#         'grand_total_range': grand_total_range,  # Include the total grand total of the filtered range
#         'unpaid_total_range': unpaid_total_range,  # Include the total unpaid amount for the filtered range
#         'outstanding_total_range': outstanding_total_range  # Include the total outstanding amount for the filtered range
#     }


import frappe
from frappe.utils import today
from datetime import datetime

@frappe.whitelist()
def fetch_invoices_and_stock_entries(start_date, end_date, warehouse, cost_center=None):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    query = """
        SELECT 
            si.name AS invoice_name, 
            si.posting_date, 
            si.status,
            si.customer, 
            si.grand_total,
            si.outstanding_amount,
            sii.item_code,
            sii.item_name,
            sii.qty,
            sii.rate,
            sii.warehouse,
            sii.cost_center
        FROM 
            `tabSales Invoice` si
        LEFT JOIN 
            `tabSales Invoice Item` sii ON si.name = sii.parent
        WHERE 
            si.docstatus = 1
            AND si.posting_date BETWEEN %s AND %s
            AND sii.warehouse = %s
    """

    if cost_center:
        query += " AND sii.cost_center = %s"
        params = (start_date, end_date, warehouse, cost_center)
    else:
        params = (start_date, end_date, warehouse)

    sales_invoices = frappe.db.sql(query, params, as_dict=True)

    grouped_invoices = {}
    grand_total_range = 0
    unpaid_total_range = 0
    outstanding_total_range = 0

    for invoice in sales_invoices:
        invoice_name = invoice['invoice_name']

        if invoice_name not in grouped_invoices:
            grouped_invoices[invoice_name] = {
                'invoice_name': invoice_name,
                'posting_date': invoice['posting_date'],
                'status': invoice['status'],
                'customer': invoice['customer'],
                'grand_total': invoice['grand_total'],
                'items': [],
                'opening_stock': 0,
                'closing_stock': 0,
                'outstanding_amount': invoice['outstanding_amount'],
                'unpaid_amount': invoice['outstanding_amount'] if invoice['outstanding_amount'] > 0 else 0,
            }
            grand_total_range += invoice['grand_total']
            outstanding_total_range += invoice['outstanding_amount']
            if invoice['outstanding_amount'] > 0:
                unpaid_total_range += invoice['outstanding_amount']

        item_code = invoice['item_code']

        # Check if the item is a bundled item and part of the invoice
        bundled_items = frappe.db.sql("""
            SELECT item_code, qty
            FROM `tabProduct Bundle Item`
            WHERE parent = %s
        """, item_code, as_dict=True)

        if bundled_items:
            for bundle_item in bundled_items:
                component_code = bundle_item['item_code']
                component_qty = bundle_item['qty'] * invoice['qty']  # Adjust for invoice quantity

                # Fetch stock ledger for the component
                opening_stock = frappe.db.sql(""" 
                    SELECT sle.`qty_after_transaction` AS opening_stock 
                    FROM `tabStock Ledger Entry` sle 
                    WHERE sle.item_code = %s 
                        AND sle.warehouse = %s
                        AND sle.posting_datetime < %s
                    ORDER BY sle.posting_datetime DESC
                    LIMIT 1
                """, (component_code, warehouse, start_date), as_dict=True)

                opening_stock = opening_stock[0].get('opening_stock', 0) if opening_stock else 0

                total_qty_sold = sum(
                    sle['actual_qty'] for sle in frappe.db.sql("""
                        SELECT actual_qty
                        FROM `tabStock Ledger Entry` sle
                        WHERE sle.item_code = %s 
                            AND sle.warehouse = %s
                            AND DATE(sle.posting_datetime) BETWEEN %s AND %s
                    """, (component_code, warehouse, start_date, end_date), as_dict=True)
                )

                closing_stock = opening_stock + total_qty_sold

                grouped_invoices[invoice_name]['items'].append({
                    'item_code': component_code,
                    'item_name': f"Component of {item_code}",
                    'si_qty': component_qty,
                    'stock_qty': total_qty_sold,
                    'rate': invoice['rate'],
                    'warehouse': warehouse,
                    'cost_center': invoice['cost_center'],
                    'opening_stock': opening_stock,
                    'closing_stock': closing_stock
                })

                grouped_invoices[invoice_name]['opening_stock'] += opening_stock
                grouped_invoices[invoice_name]['closing_stock'] += closing_stock
        else:
            # Non-bundled item logic remains unchanged
            opening_stock = frappe.db.sql(""" 
                SELECT sle.`qty_after_transaction` AS opening_stock 
                FROM `tabStock Ledger Entry` sle 
                WHERE sle.item_code = %s 
                    AND sle.warehouse = %s
                    AND sle.posting_datetime < %s
                ORDER BY sle.posting_datetime DESC
                LIMIT 1
            """, (item_code, warehouse, start_date), as_dict=True)

            opening_stock = opening_stock[0].get('opening_stock', 0) if opening_stock else 0

            total_qty_sold = sum(
                sle['actual_qty'] for sle in frappe.db.sql("""
                    SELECT actual_qty
                    FROM `tabStock Ledger Entry` sle
                    WHERE sle.item_code = %s 
                        AND sle.warehouse = %s
                        AND DATE(sle.posting_datetime) BETWEEN %s AND %s
                """, (item_code, warehouse, start_date, end_date), as_dict=True)
            )

            closing_stock = opening_stock + total_qty_sold

            grouped_invoices[invoice_name]['items'].append({
                'item_code': item_code,
                'item_name': invoice['item_name'],
                'si_qty': invoice['qty'],
                'stock_qty': total_qty_sold,
                'rate': invoice['rate'],
                'warehouse': invoice['warehouse'],
                'cost_center': invoice['cost_center'],
                'opening_stock': opening_stock,
                'closing_stock': closing_stock
            })

            grouped_invoices[invoice_name]['opening_stock'] += opening_stock
            grouped_invoices[invoice_name]['closing_stock'] += closing_stock

    return {
        'grouped_invoices': list(grouped_invoices.values()),
        'grand_total_range': grand_total_range,
        'unpaid_total_range': unpaid_total_range,
        'outstanding_total_range': outstanding_total_range
    }
