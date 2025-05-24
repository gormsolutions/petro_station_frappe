import frappe
from frappe import _

@frappe.whitelist()
def fetch_transit_warehouse(warehouse):
    # Get the Warehouse doc by name
    doc = frappe.get_doc("Warehouse", warehouse)

    return {
        "status": "success",
        "default_in_transit_warehouse": doc.default_in_transit_warehouse,
        "items": doc.custom_warehouse_items
    }
