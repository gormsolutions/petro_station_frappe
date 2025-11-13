import frappe

@frappe.whitelist()
def fetch_actual_qty_grouped_by_warehouse_others(warehouse_filter=None):
    try:
        # Query to fetch required fields from the Bin doctype grouped by Warehouse
        query = """
            SELECT 
                warehouse,
                item_code,
                SUM(actual_qty) AS total_actual_qty,
                AVG(valuation_rate) AS avg_valuation_rate,
                GROUP_CONCAT(DISTINCT stock_uom) AS uoms
            FROM
                `tabBin`
            WHERE
                (%(warehouse)s IS NULL OR warehouse = %(warehouse)s)
            GROUP BY
                warehouse, item_code
            ORDER BY
                warehouse, item_code
        """

        # Execute the query with the filter
        result = frappe.db.sql(query, {"warehouse": warehouse_filter}, as_dict=True)


        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in fetching actual qty grouped by warehouse")
        frappe.throw(f"An error occurred: {str(e)}")


import frappe

@frappe.whitelist()
def fetch_actual_qty_grouped_by_warehouse(warehouse_filter=None):
    try:
        query = """
            SELECT 
                b.warehouse,
                b.item_code,
                w.custom_gas_stock_type,
                SUM(b.actual_qty) AS total_actual_qty,
                AVG(b.valuation_rate) AS avg_valuation_rate,
                GROUP_CONCAT(DISTINCT b.stock_uom) AS uoms
            FROM
                `tabBin` b
            JOIN
                `tabWarehouse` w ON b.warehouse = w.name
            JOIN
                `tabItem` i ON b.item_code = i.name
            WHERE
                (%(warehouse)s IS NULL OR b.warehouse = %(warehouse)s)
                AND w.custom_gas_stock_type IN ('Refill', 'Empties')
                AND (
                    (w.custom_gas_stock_type = 'Refill' AND i.custom_gas_stock_entry_name = 'Refill')
                    OR (w.custom_gas_stock_type = 'Empties' AND i.custom_gas_stock_entry_name = 'Empties')
                    OR (i.custom_gas_stock_entry_name = 'Non Cylinder')
                )
            GROUP BY
                b.warehouse, b.item_code
            ORDER BY
                b.warehouse, b.item_code
        """

        result = frappe.db.sql(query, {"warehouse": warehouse_filter}, as_dict=True)
        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in fetching actual qty grouped by warehouse")
        frappe.throw(f"An error occurred: {str(e)}")

import frappe
from frappe.utils import get_datetime, now_datetime

@frappe.whitelist()
def get_qty_as_of_date(as_of_date=None):
    docname = "rvua8f0v83"
    doc = frappe.get_doc("Stock Items", docname)

    if not as_of_date:
        # Default to today if no date provided
        as_of_date = now_datetime().strftime("%Y-%m-%d")

    # Convert user date to end of day datetime string
    # e.g. "2025-07-10" → "2025-07-10 23:59:59"
    as_of_datetime = f"{as_of_date} 23:59:59"

    item_map = {}
    for item in doc.current_stock_items:
        item_map.setdefault(item.item_type, []).append(item.item_code)

    warehouse_map = {}
    for wh in doc.current_stock_warehouse:
        warehouse_map.setdefault(wh.item_type, []).append(wh.warehouse)

    result = {}

    for item_type, item_codes in item_map.items():
        result.setdefault(item_type, {})

        if item_type == "Extras":
            warehouses = warehouse_map.get("Gas", [])
        else:
            warehouses = warehouse_map.get(item_type, [])

        for warehouse in warehouses:
            result[item_type].setdefault(warehouse, [])

            for item_code in item_codes:
                qty_data = frappe.db.sql("""
                    SELECT qty_after_transaction
                    FROM `tabStock Ledger Entry`
                    WHERE item_code = %s
                      AND warehouse = %s
                      AND posting_datetime <= %s
                      AND is_cancelled = 0
                    ORDER BY posting_datetime DESC
                    LIMIT 1
                """, (item_code, warehouse, as_of_datetime), as_dict=True)

                result[item_type][warehouse].append({
                    "item_code": item_code,
                    "qty_after_transaction": qty_data[0].qty_after_transaction if qty_data else 0
                })

    return result


import frappe
from frappe.utils import now_datetime

import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def qty_as_of_date(as_of_date=None):
    docname = "rvua8f0v83"
    doc = frappe.get_doc("Stock Items", docname)

    if not as_of_date:
        as_of_date = now_datetime().strftime("%Y-%m-%d")

    item_map = {}
    for item in doc.current_stock_items:
        item_map.setdefault(item.item_type, []).append(item.item_code)

    warehouse_map = {}
    for wh in doc.current_stock_warehouse:
        warehouse_map.setdefault(wh.item_type, []).append(wh.warehouse)

    result = {}

    for item_type, item_codes in item_map.items():
        result.setdefault(item_type, {})

        # Extras use Gas warehouses
        warehouses = warehouse_map.get("Gas" if item_type == "Extras" else item_type, [])

        for warehouse in warehouses:
            result[item_type].setdefault(warehouse, [])

            for item_code in item_codes:
                # Purchases (non-return)
                purchase_received = frappe.db.sql("""
                    SELECT SUM(qty) AS total
                    FROM `tabPurchase Invoice Item` pii
                    JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                    WHERE pii.item_code = %s
                      AND pii.warehouse = %s
                      AND pi.is_return = 0
                      AND pi.docstatus = 1
                      AND pi.posting_date = %s
                """, (item_code, warehouse, as_of_date), as_dict=True)[0].total or 0

                # Purchase returns
                purchase_returned = frappe.db.sql("""
                    SELECT SUM(qty) AS total
                    FROM `tabPurchase Invoice Item` pii
                    JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
                    WHERE pii.item_code = %s
                      AND pii.warehouse = %s
                      AND pi.is_return = 1
                      AND pi.docstatus = 1
                      AND pi.posting_date = %s
                """, (item_code, warehouse, as_of_date), as_dict=True)[0].total or 0

                # Stock Entry Material Receipt
                stock_entry_received = frappe.db.sql("""
                    SELECT SUM(qty) AS total
                    FROM `tabStock Entry Detail` sed
                    JOIN `tabStock Entry` se ON se.name = sed.parent
                    WHERE sed.item_code = %s
                      AND sed.t_warehouse = %s
                      AND se.stock_entry_type = 'Material Receipt'
                      AND se.docstatus = 1
                      AND se.posting_date = %s
                """, (item_code, warehouse, as_of_date), as_dict=True)[0].total or 0

                # Sales Qty from Stock Ledger Entry
                sales_qty = frappe.db.sql("""
                    SELECT SUM(actual_qty) AS total
                    FROM `tabStock Ledger Entry`
                    WHERE item_code = %s
                      AND warehouse = %s
                      AND voucher_type = 'Sales Invoice'
                      AND posting_date = %s
                """, (item_code, warehouse, as_of_date), as_dict=True)[0].total or 0

                total_purchase_received = purchase_received + stock_entry_received

                result[item_type][warehouse].append({
                    "item_code": item_code,
                    "purchase_received": total_purchase_received,
                    "purchase_returned": purchase_returned,
                    "sales_qty": sales_qty
                })

    return result
