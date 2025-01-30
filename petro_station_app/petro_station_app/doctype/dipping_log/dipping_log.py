# # import frappe
# from frappe.model.document import Document
# import frappe

# class DippingLog(Document):
#     def validate(self):
#         # Check if a DippingLog entry already exists for the same tank, branch, and date (only for new documents)
#         if self.is_new():
#             existing_log = frappe.db.exists({
#                 'doctype': 'Dipping Log',
#                 'tank': self.tank,
#                 'branch': self.branch,
#                 'dipping_date': self.dipping_date
#             })
            
#             if existing_log:
#                 frappe.throw(f"A DippingLog entry already exists for tank {self.tank}, branch {self.branch} on {self.dipping_date}.")

#         # Ensure the gain or loss is within the allowed range
#         if self.dipping_difference is not None and (self.dipping_difference < -150 or self.dipping_difference > 150):
#             frappe.throw("The dipping Level difference should be between (Gain) Of-1000 and (Loss) of 150.")
    
#     def on_submit(self):
#         if self.dipping_difference is None or self.dipping_difference == 0:
#             return  # Skip creating Stock Entry if there is no difference

#         # Determine the type of Stock Entry and the warehouses
#         if self.dipping_difference > 0:
#             stock_entry_type = "Material Issue"
#             message = "A loss has been issued."
#             source_warehouse = self.tank
#             target_warehouse = None
#         else:
#             stock_entry_type = "Material Receipt"
#             message = "A gain has been received."
#             source_warehouse = None
#             target_warehouse = self.tank

#         # Create the Stock Entry
#         stock_entry = frappe.get_doc({
#             "doctype": "Stock Entry",
#             "stock_entry_type": stock_entry_type,
#             "posting_date": self.dipping_date,
#             "posting_time": self.dipping_time,
#             "set_posting_time": 1,
#             "custom_dipping_log_id": self.name,
#             "items": [{
#                 "item_code": self.item_code,
#                 "s_warehouse": source_warehouse,
#                 "t_warehouse": target_warehouse,
#                 "cost_center": self.branch,
#                 "qty": abs(self.dipping_difference)  # Ensure the quantity is always positive
#             }]
#         })
        
#         # Insert and submit the Stock Entry
#         stock_entry.insert()
#         stock_entry.submit()
        
#         # Display the message
#         frappe.msgprint(message)


# import frappe
from frappe.model.document import Document
import frappe

class DippingLog(Document):
    def validate(self):
        # Check if a DippingLog entry already exists for the same tank, branch, and date (only for new documents)
        if self.is_new():
            existing_log = frappe.db.exists({
                'doctype': 'Dipping Log',
                'tank': self.tank,
                'branch': self.branch,
                'dipping_date': self.dipping_date
            })
            
            if existing_log:
                frappe.throw(f"A DippingLog entry already exists for tank {self.tank}, branch {self.branch} on {self.dipping_date}.")

        # Ensure the gain or loss is within the allowed range
        if self.dipping_difference is not None and (self.dipping_difference < -150 or self.dipping_difference > 150):
            frappe.throw("The dipping Level difference should be between (Gain) Of -150 and (Loss) of 150.")
    
    def on_submit(self):
        if self.dipping_difference is None or self.dipping_difference == 0:
            return  # Skip creating Stock Reconciliation if there is no difference

        # Prepare Stock Reconciliation data
        stock_reconciliation = frappe.get_doc({
            "doctype": "Stock Reconciliation",
            "posting_date": self.dipping_date,
            "posting_time": self.dipping_time,
            "set_posting_time": 1,
            "cost_center": self.branch,  # Assuming 'branch' represents the company
            "custom_dipping_log_id": self.name,
            "items": [{
                "item_code": self.item_code,
                "warehouse": self.tank,
                "qty": self.current_dipping_level,  # Adjust quantity based on the current stock level
                # "valuation_rate": self.get_item_valuation_rate()  # Fetch the item's valuation rate
            }]
        })
        
        # Insert and submit the Stock Reconciliation
        stock_reconciliation.insert()
        stock_reconciliation.submit()
        
        # Display success message
        frappe.msgprint("Stock Reconciliation has been successfully created.")
    
    def get_existing_qty(self):
        # Get the current stock quantity in the warehouse
        existing_qty = frappe.db.get_value("Bin", {"item_code": self.item_code, "warehouse": self.tank}, "actual_qty")
        return existing_qty or 0
    
    def get_item_valuation_rate(self):
        # Fetch the item's valuation rate
        valuation_rate = frappe.db.get_value("Item", {"item_code": self.item_code}, "valuation_rate")
        if not valuation_rate:
            frappe.throw(f"Valuation rate is not set for item {self.item_code}.")
        return valuation_rate
