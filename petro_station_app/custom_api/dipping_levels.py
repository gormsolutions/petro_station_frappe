import frappe
from frappe import _

# @frappe.whitelist()
# def get_warehouse_from_tank(tank):
#     bin = frappe.get_all("Bin", filters={"Warehouse": tank}, fields=["actual_qty", "item_code"])
#     return bin

@frappe.whitelist()
def get_warehouse_from_tank(tank):
    # Get distinct item codes from Stock Ledger Entry for the given warehouse (tank)
    # that are not cancelled (is_cancelled = 0)
    distinct_items = frappe.db.get_all(
        "Stock Ledger Entry",
        filters={"warehouse": tank, "is_cancelled": 0},
        fields=["DISTINCT item_code as item_code"]
    )

    data = []
    for item in distinct_items:
        # Fetch the exact qty_after_transaction from the most recent non-cancelled Stock Ledger Entry
        actual_qty = frappe.db.get_value(
            "Stock Ledger Entry",
            filters={
                "item_code": item.item_code,
                "warehouse": tank,
                "is_cancelled": 0
            },
            fieldname="qty_after_transaction",
            order_by="posting_date DESC, posting_time DESC, name DESC"
        ) or 0

        data.append({
            "item_code": item.item_code,
            "actual_qty": actual_qty
        })

    return data
    
@frappe.whitelist()
def fetch_dipping_logs(branch, dipping_date):
    # Fetch Dipping Log documents with filters
    dipping_logs = frappe.get_all(
        'Dipping Log',  # Doctype name
        fields=['*'],   # Fetch all fields
        filters={
            'branch': branch,         # Filter by branch
            'dipping_date': dipping_date  # Filter by dipping_date
        }
    )
    return dipping_logs

