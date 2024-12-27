import frappe
@frappe.whitelist()
def update_parent_item_groups():
    # Fetch Item Price records with item_code 'BUTTER COOKIES'
    item_prices = frappe.get_all(
        'Item Price',
        fields=['name', 'item_code'],
        # filters={'item_code': 'BUTTER COOKIES'}
    )
    
    for item_price in item_prices:
        if item_price['item_code']:
            # Fetch item_group from the linked Item
            item_group = frappe.db.get_value('Item', item_price['item_code'], 'item_group')
            
            if item_group:
                # Fetch the parent item group from the Item Group doctype
                parent_item_group = frappe.db.get_value('Item Group', item_group, 'parent_item_group')
                
                if parent_item_group:
                    # Update custom_item_group in the Item Price record
                    frappe.db.set_value('Item Price', item_price['name'], 'custom_item_group', parent_item_group)
    
    frappe.db.commit()
    return {"status": "success", "updated_count": len(item_prices)}
