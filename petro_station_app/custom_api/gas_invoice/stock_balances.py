import frappe

@frappe.whitelist()
def fetch_actual_qty_grouped_by_warehouse(warehouse_filter=None):
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
