# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import nowdate

class DippingLog(Document):
    def validate(self):
        if self.dipping_date > nowdate():
            frappe.throw(
                f"A DippingLog is not allowed for future dates beyond {nowdate()}."
            )

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
        if self.dipping_difference is not None and (self.dipping_difference < -500 or self.dipping_difference > 500):
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
        # Query the latest Stock Ledger Entry for this item and warehouse
        qty = frappe.db.sql("""
            SELECT actual_qty
            FROM `tabStock Ledger Entry`
            WHERE item_code = %(item_code)s
            AND warehouse = %(warehouse)s
            ORDER BY posting_date DESC, posting_time DESC, name DESC
            LIMIT 1
        """, {
            "item_code": self.item_code,
            "warehouse": self.tank
        }, as_dict=True)

        # If an entry is found, return its actual_qty; otherwise, return 0
        if qty:
            return qty[0].actual_qty or 0
        return 0

    
    def get_item_valuation_rate(self):
        # Fetch the item's valuation rate
        valuation_rate = frappe.db.get_value("Item", {"item_code": self.item_code}, "valuation_rate")
        if not valuation_rate:
            frappe.throw(f"Valuation rate is not set for item {self.item_code}.")
        return valuation_rate
