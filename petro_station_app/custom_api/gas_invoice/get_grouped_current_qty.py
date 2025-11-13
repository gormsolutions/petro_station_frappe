import frappe
from collections import OrderedDict
from erpnext.stock.utils import get_stock_balance

@frappe.whitelist()
def get_matrix_stock_summary(docname):
    doc = frappe.get_doc("Stock Items", docname)

    warehouse_list = [w.warehouse for w in doc.current_stock_warehouse]

    # Warehouses to exclude by item type
    empties_exclude_warehouses = {"Gulu Gas Store - SE", "Jinja Gas Stock", "Mbale Gas Store - SE"}
    empty_cylinder_warehouses = {"Empty Cylinder Mbale Store - SE", "Empty Cylinders Gulu Depot - SE", "Empty Cylinders Jinja Depot - SE"}

    grouped_summary = OrderedDict()

    totals_by_type = {
        "EMPTIES": 0,
        "GAS": 0,
        "EXTRAS": 0
    }

    for item in doc.current_stock_items:
        item_code = item.item_code.strip()
        item_type_saved = (item.type or "").strip()

        if item_type_saved:
            item_type = item_type_saved.upper()
        else:
            item_code_upper = item_code.upper()
            if "GAS" in item_code_upper:
                item_type = "GAS"
            elif "EMPTY" in item_code_upper:
                item_type = "EMPTIES"
            else:
                item_type = "EXTRAS"

        if item_type not in grouped_summary:
            grouped_summary[item_type] = OrderedDict()

        if item_code not in grouped_summary[item_type]:
            # Determine warehouses to include based on item type
            if item_type == "EMPTIES":
                # Exclude gas warehouses
                filtered_warehouses = [wh for wh in warehouse_list if wh not in empties_exclude_warehouses]
            elif item_type == "GAS":
                # Exclude empty cylinder warehouses
                filtered_warehouses = [wh for wh in warehouse_list if wh not in empty_cylinder_warehouses]
            elif item_type == "EXTRAS":
                # Exclude empty cylinder warehouses as well
                filtered_warehouses = [wh for wh in warehouse_list if wh not in empty_cylinder_warehouses]
            else:
                filtered_warehouses = warehouse_list

            grouped_summary[item_type][item_code] = {wh: 0 for wh in filtered_warehouses}
            grouped_summary[item_type][item_code]["TOTAL"] = 0

        total_qty_for_item = 0

        # Select warehouses to count quantities for, same logic as above
        if item_type == "EMPTIES":
            warehouses_to_count = [wh for wh in warehouse_list if wh not in empties_exclude_warehouses]
        elif item_type == "GAS":
            warehouses_to_count = [wh for wh in warehouse_list if wh not in empty_cylinder_warehouses]
        elif item_type == "EXTRAS":
            warehouses_to_count = [wh for wh in warehouse_list if wh not in empty_cylinder_warehouses]
        else:
            warehouses_to_count = warehouse_list

        for wh in warehouses_to_count:
            qty = get_stock_balance(item_code, wh) or 0
            grouped_summary[item_type][item_code][wh] = qty
            total_qty_for_item += qty

        grouped_summary[item_type][item_code]["TOTAL"] = total_qty_for_item

        if item_type in totals_by_type:
            totals_by_type[item_type] += total_qty_for_item
        else:
            totals_by_type[item_type] = total_qty_for_item

    return {
        "warehouses": warehouse_list,
        "grouped_summary": grouped_summary,
        "totals_by_type": totals_by_type
    }


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

    # Convert input datetime
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

            grouped_summary[item_type][item_code] = {wh: 0 for wh in filtered_warehouses}
            grouped_summary[item_type][item_code]["TOTAL"] = 0

        total_qty_for_item = 0

        for wh in grouped_summary[item_type][item_code]:
            if wh == "TOTAL":
                continue
            qty = get_qty_as_of(item_code, wh, posting_datetime)
            grouped_summary[item_type][item_code][wh] = qty
            total_qty_for_item += qty

        grouped_summary[item_type][item_code]["TOTAL"] = total_qty_for_item
        totals_by_type[item_type] += total_qty_for_item

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

import frappe
import json

@frappe.whitelist()
def submit_stock_verification(data, as_of_date=None, store=None):
    if isinstance(data, str):
        data = json.loads(data)

    if not store or not isinstance(store, str):
        frappe.throw("Store must be a string and not empty")

    if not as_of_date:
        as_of_date = frappe.utils.today()

    doc = frappe.new_doc("Custom Stock Verification")
    doc.date = as_of_date
    doc.store = store  # This is a string like "Jinja"

    # data is a dict of item_code -> warehouse -> details
    stock_data = data

    for item_code, warehouses in stock_data.items():
        for warehouse_name, details in warehouses.items():
            physical_qty = details.get("physical_qty")
            if physical_qty and float(physical_qty) != 0:
                doc.append("items", {
                    "item": item_code,
                    "warehouse": warehouse_name,
                    "system_qty": details.get("system_qty", 0),
                    "physical_qty": physical_qty,
                    "difference": details.get("difference", 0)
                })

    if not doc.items:
        frappe.throw("No physical quantities entered. Nothing to submit.")

    doc.insert(ignore_permissions=True)
    doc.submit()

    return {"status": "success", "name": doc.name}
