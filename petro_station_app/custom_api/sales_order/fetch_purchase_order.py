import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def map_purchase_order_to_purchase_management(source_name, target_doc=None):
    def set_missing_values(source, target):
        # Calculate total_qty and grand_total
        total_qty = 0
        grand_total = 0
        for item in target.items:
            item.amount = (item.qty or 0) * (item.rate or 0)  # Ensure amount is calculated
            total_qty += item.qty or 0
            grand_total += item.amount or 0

        target.total_qty = total_qty
        target.grand_totals = grand_total

        target.run_method("set_missing_values")

    def postprocess_parent(source_doc, target_doc, source_parent):
        target_doc.supplier = source_doc.supplier
        target_doc.purchase_order_number = source_doc.name
        target_doc.transaction_date = source_doc.transaction_date
        target_doc.schedule_date = source_doc.schedule_date
        target_doc.price_list = source_doc.buying_price_list
        target_doc.cost_center = source_doc.cost_center
        target_doc.branch = source_doc.branch
        target_doc.location = source_doc.location

    def postprocess_child(source_doc, target_doc, source_parent):
        target_doc.price_list = source_parent.buying_price_list
        target_doc.uom = source_doc.uom
        # Set qty to remaining qty
        target_doc.qty = source_doc.qty - source_doc.received_qty
        # Calculate amount
        target_doc.amount = (target_doc.qty or 0) * (target_doc.rate or 0)

    target_doc = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Management",
                "field_map": {
                    "name": "purchase_order_number",
                    "supplier": "supplier"
                },
                "postprocess": postprocess_parent,
            },
            "Purchase Order Item": {
                "doctype": "Purchase Management Items",
                "field_map": {
                    "item_code": "item",
                    "item_name": "item_name",
                    "rate": "rate",
                    "cost_center": "cost_center",
                    "warehouse": "warehouse",
                    "uom": "uom"
                },
                "condition": lambda doc: (doc.qty - doc.received_qty) > 0,
                "postprocess": postprocess_child
            },
        },
        target_doc,
        set_missing_values
    )

    return target_doc
