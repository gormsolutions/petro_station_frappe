import frappe
from frappe import _

# @frappe.whitelist()
# def get_warehouse_from_tank(tank):
#     bin = frappe.get_all("Bin", filters={"Warehouse": tank}, fields=["actual_qty", "item_code"])
#     return bin

# @frappe.whitelist()
# def get_warehouse_from_tank(tank):
#     # Get distinct item codes from Stock Ledger Entry for the given warehouse (tank)
#     # that are not cancelled (is_cancelled = 0)
#     distinct_items = frappe.db.get_all(
#         "Stock Ledger Entry",
#         filters={"warehouse": tank, "is_cancelled": 0},
#         fields=["DISTINCT item_code as item_code"]
#     )

#     data = []
#     for item in distinct_items:
#         # Fetch the exact qty_after_transaction from the most recent non-cancelled Stock Ledger Entry
#         actual_qty = frappe.db.get_value(
#             "Stock Ledger Entry",
#             filters={
#                 "item_code": item.item_code,
#                 "warehouse": tank,
#                 "is_cancelled": 0
#             },
#             fieldname="qty_after_transaction",
#             order_by="posting_date DESC, posting_time DESC, name DESC"
#         ) or 0

#         data.append({
#             "item_code": item.item_code,
#             "actual_qty": actual_qty
#         })

#     return data
import frappe

@frappe.whitelist()
def get_warehouse_from_tank(tank):
    # Get all distinct item codes from Stock Ledger Entry (non-cancelled only)
    distinct_items = frappe.db.sql(
        """
        SELECT DISTINCT item_code
        FROM `tabStock Ledger Entry`
        WHERE warehouse = %s AND is_cancelled = 0
        """,
        (tank,),
        as_dict=True,
    )

    data = []
    for item in distinct_items:
        # Fetch the most recent non-cancelled SLE entry for this item in the given tank
        sle = frappe.db.sql(
            """
            SELECT qty_after_transaction
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
              AND warehouse = %s
              AND is_cancelled = 0
            ORDER BY posting_date DESC, posting_time DESC, name DESC
            LIMIT 1
            """,
            (item.item_code, tank),
            as_dict=True,
        )

        data.append({
            "item_code": item.item_code,
            "actual_qty": sle[0].qty_after_transaction if sle else 0
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


import frappe
from erpnext.stock.utils import get_stock_balance


def set_cost_price(doc, method):

    if not doc.item_code or not doc.tank:
        return

    # Get valuation rate exactly like Stock Reconciliation
    stock_balance = get_stock_balance(
        doc.item_code,
        doc.tank,
        with_valuation_rate=True
    )

    # stock_balance = (qty, valuation_rate)
    valuation_rate = stock_balance[1]

    if not valuation_rate:
        frappe.throw(f"Valuation rate not found for Item {doc.item_code} in {doc.tank}")

    # ✅ Set it to cost_price
    doc.cost_price = valuation_rate

