import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

@frappe.whitelist()
def map_sales_order_to_fuel_sales(source_name, target_doc=None):
    def set_missing_values(source, target):
        target.run_method("set_missing_values")

    def postprocess_parent(source_doc, target_doc, source_parent):
        target_doc.customer = source_doc.customer
        target_doc.sales_order_number = source_doc.name

    def postprocess_child(source_doc, target_doc, source_parent):
        target_doc.price_list = source_parent.selling_price_list

        # Compute remaining_qty = qty - billed_qty (approximated as billed_amt / rate)
        billed_qty = flt(source_doc.billed_amt) / flt(source_doc.rate) if flt(source_doc.rate) else 0
        remaining_qty = flt(source_doc.qty) - billed_qty

        target_doc.qty = remaining_qty
        target_doc.amount = remaining_qty * flt(source_doc.rate)

        pos_profile = frappe.db.get_value("POS Profile", {"warehouse": source_doc.warehouse}, "name")
        target_doc.pos_profile = pos_profile or ""

    target_doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Fuel Sales App",
                "field_map": {
                    "name": "sales_order_number"
                },
                "postprocess": postprocess_parent
            },
            "Sales Order Item": {
                "doctype": "Fuel Sales Items",
                "field_map": {
                    "item_code": "item",
                    "item_name": "item_name",
                    "rate": "rate",
                    "uom": "uom",
                    "warehouse": "warehouse",
                    "price_list_rate": "price_list"
                },
                "condition": lambda doc: (flt(doc.qty) - (flt(doc.billed_amt) / flt(doc.rate) if flt(doc.rate) else 0)) > 0,
                "postprocess": postprocess_child
            },
        },
        target_doc,
        set_missing_values
    )

    return target_doc
