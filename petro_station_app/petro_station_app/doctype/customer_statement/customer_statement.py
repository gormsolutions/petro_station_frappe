# Copyright (c) 2024, mututa paul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.model.document import Document
import frappe  # type: ignore
from frappe import _  # type: ignore
from frappe.utils import add_days, nowdate, nowtime


class CustomerStatement(Document):
    def on_update(self):
        if self.stationary_charges > 0:
            self.create_sales_invoice()

    def create_sales_invoice(self):
        # Check if a Sales Invoice already exists for this transaction
        existing_sales_invoice = frappe.db.exists("Sales Invoice", {
            "custom_stationery_credit_id": self.name,
            "docstatus": 1
        })
        if existing_sales_invoice:
            frappe.msgprint(_("A Sales Invoice for Stationery Charges already exists for this transaction"), alert=True)
            return

        # Validate required fields
        if not self.customer:
            frappe.throw(_("Customer is required to create a Sales Invoice"))

        # Create a new Sales Invoice
        try:
            sales_invoice = frappe.new_doc("Sales Invoice")
            sales_invoice.customer = self.customer
            sales_invoice.due_date = add_days(nowdate(), 15)
            sales_invoice.cost_center = self.station
            sales_invoice.update_stock = 1
            sales_invoice.set_posting_time = 1
            sales_invoice.posting_date = nowdate()
            sales_invoice.posting_time = nowtime()
            sales_invoice.custom_stationery_credit_id = self.name
            sales_invoice.custom_employee = self.staff

            # Add items to the Sales Invoice
            sales_invoice.append("items", {
                "item_code": "STATIONERY CHARGES",
                "qty": 1,
                "rate": self.stationary_charges,
                "cost_center": self.station,
            })

            # Save and submit the Sales Invoice
            sales_invoice.insert()
            sales_invoice.submit()

            frappe.msgprint(_("Stationery Charges have been invoiced and submitted successfully"), alert=True)

            # Create associated Customer Document
            self.create_new_customer_documents()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Failed to create Sales Invoice"))
            frappe.throw(_("An error occurred while creating the Sales Invoice: {0}").format(str(e)))

    def create_new_customer_documents(self):
        # Check if a Customer Document already exists for this transaction
        existing_customer_doc = frappe.db.exists("Customer Document", {
            "stationery_credit_id": self.name
        })
        if existing_customer_doc:
            frappe.msgprint(_("A Customer Document already exists for this transaction"), alert=True)
            return

        # Validate required fields
        if not self.customer or not self.stationary_charges:
            frappe.throw(_("Customer and Stationary Charges are required to create a Customer Document"))

        # Create a new Customer Document
        try:
            cust_doc = frappe.get_doc({
                "doctype": "Customer Document",
                "customer": self.customer,
                "customer_name": self.customer_name,
                "station": self.station,
                "posting_date": nowdate(),
                "time": nowtime(),
                "due_date": add_days(nowdate(), 15),
                "net_total": 0,
                "total_qty": 0,
                "grand_totals": 0,
                "stationery_credit_id": self.name
            })

            cust_doc.append("items", {
                "price_list": "Standard Selling",
                "pos_profile": "Elgon AGO P4",
                "item_code": "STATIONERY CHARGES",
                "qty": 1,
                "rate": self.stationary_charges,
                "amount": self.stationary_charges,
            })

            # Update totals
            cust_doc.total_qty = 1
            cust_doc.grand_totals = self.stationary_charges

            # Insert and submit the Customer Document
            cust_doc.insert()
            cust_doc.submit()

            frappe.msgprint(_("Customer Document {0} created and submitted").format(cust_doc.name), alert=True)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Failed to create Customer Document"))
            frappe.throw(_("An error occurred while creating the Customer Document: {0}").format(str(e)))
