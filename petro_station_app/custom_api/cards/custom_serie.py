import frappe
from frappe.model.meta import get_meta

@frappe.whitelist()
def add_all_fields_to_delivery_note_document():
    target_doc = frappe.get_doc("DocType", "Delivery Note Document")
    source_meta = get_meta("Delivery Note")

    existing_fields = {df.fieldname for df in target_doc.fields}

    added_fields = 0

    for df in source_meta.fields:
        # Skip custom fields
        if df.get("custom_field"):
            continue
        
        # Avoid duplicate fields
        if df.fieldname in existing_fields:
            continue
        
        new_df = df.as_dict()
        # Remove system properties that cause errors during insertion
        for key in ["idx", "parent", "parentfield", "parenttype", "modified", "modified_by", 
                    "creation", "owner", "docstatus", "doctype", "name"]:
            new_df.pop(key, None)

        target_doc.append("fields", new_df)
        added_fields += 1

    target_doc.save()
    frappe.db.commit()
    return f"{added_fields} fields (including child tables) copied from Delivery Note to Delivery Note Document."
