import frappe
from frappe import _

@frappe.whitelist()
def get_warehouse_from_tank(tank):
    bin = frappe.get_all("Bin", filters={"Warehouse": tank}, fields=["actual_qty", "item_code"])
    return bin
    
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

