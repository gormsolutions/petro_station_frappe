import frappe
from collections import OrderedDict
from frappe.utils import get_datetime

@frappe.whitelist()
def get_matrix_stock_summary(docname, posting_datetime=None):
    doc = frappe.get_doc("Stock Items", docname)

    warehouse_list = [w.warehouse for w in doc.current_stock_warehouse]

    empties_exclude_warehouses = {"Gulu Gas Store - SE", "Jinja Gas Stock", "Mbale Gas Store - SE"}
    empty_cylinder_warehouses = {
        "Empty Cylinder Mbale Store - SE", "Empty Cylinders Gulu Depot - SE", "Empty Cylinders Jinja Depot - SE"
    }

    grouped_summary = OrderedDict()
    totals_by_type = {"EMPTIES": 0, "GAS": 0, "EXTRAS": 0}

    posting_datetime = get_datetime(posting_datetime) if posting_datetime else frappe.utils.now_datetime()

    for item in doc.current_stock_items:
        item_code = item.item_code.strip()
        item_type_saved = (item.type or "").strip()
        item_type = item_type_saved.upper() if item_type_saved else (
            "GAS" if "GAS" in item_code.upper()
            else "EMPTIES" if "EMPTY" in item_code.upper()
            else "EXTRAS"
        )

        if item_type not in grouped_summary:
            grouped_summary[item_type] = OrderedDict()

        if item_code not in grouped_summary[item_type]:
            if item_type == "EMPTIES":
                filtered_warehouses = [wh for wh in warehouse_list if wh not in empties_exclude_warehouses]
            else:
                filtered_warehouses = [wh for wh in warehouse_list if wh not in empty_cylinder_warehouses]

            grouped_summary[item_type][item_code] = {
                wh: {
                    "system_qty": 0,
                    "sales_done": 0
                } for wh in filtered_warehouses
            }
            grouped_summary[item_type][item_code]["TOTAL"] = {
                "system_qty": 0,
                "sales_done": 0
            }

        total_system_qty = 0
        total_sales_done = 0

        for wh in grouped_summary[item_type][item_code]:
            if wh == "TOTAL":
                continue

            system_qty = get_qty_as_of(item_code, wh, posting_datetime)
            sales_done = get_sales_done_as_of(item_code, wh, posting_datetime)

            grouped_summary[item_type][item_code][wh]["system_qty"] = system_qty
            grouped_summary[item_type][item_code][wh]["sales_done"] = sales_done

            total_system_qty += system_qty
            total_sales_done += sales_done

        grouped_summary[item_type][item_code]["TOTAL"]["system_qty"] = total_system_qty
        grouped_summary[item_type][item_code]["TOTAL"]["sales_done"] = total_sales_done

        totals_by_type[item_type] += total_system_qty

    return {
        "warehouses": warehouse_list,
        "grouped_summary": grouped_summary,
        "totals_by_type": totals_by_type
    }

def get_qty_as_of(item_code, warehouse, posting_datetime):
    """
    Returns the stock quantity of an item in a warehouse as of a specific datetime.
    """
    qty = frappe.db.sql("""
        SELECT SUM(actual_qty) as qty
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND warehouse = %s
          AND posting_datetime <= %s
          AND is_cancelled = 0
    """, (item_code, warehouse, posting_datetime))[0][0]

    return qty or 0

def get_sales_done_as_of(item_code, warehouse, posting_datetime):
    """
    Returns total quantity sold from a warehouse as of the given posting date only (ignores time).
    """
    posting_date = posting_datetime.date()  # extract just the date

    sales_qty = frappe.db.sql("""
        SELECT SUM(si_item.qty)
        FROM `tabSales Invoice Item` si_item
        JOIN `tabSales Invoice` si ON si.name = si_item.parent
        WHERE si.docstatus = 1
          AND si_item.item_code = %s
          AND si_item.warehouse = %s
          AND si.posting_date <= %s
    """, (item_code, warehouse, posting_date))[0][0]

    return sales_qty or 0
