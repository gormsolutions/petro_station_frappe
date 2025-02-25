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
