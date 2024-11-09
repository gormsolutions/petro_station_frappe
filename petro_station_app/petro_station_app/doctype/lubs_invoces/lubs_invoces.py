# Copyright (c) 2024, mututa paul and contributors
# For license information, please see license.txt

# import frappe
import frappe  # type: ignore
from frappe.model.document import Document
from frappe import _  # type: ignore

class LubsInvoces(Document):
    def on_submit(self):
        self.create_sales_invoice()

    def create_sales_invoice(self):
        existing_sales_invoice = frappe.db.exists("Sales Invoice", {
            "custom_sales_id": self.name,
            "docstatus": 1
        })
        if existing_sales_invoice:
            frappe.msgprint(_("Sales Invoice already exists for this transaction"))
            return

        sales_invoice = frappe.new_doc("Sales Invoice")
        sales_invoice.customer = self.customer
        sales_invoice.due_date = self.due_date
        sales_invoice.allocate_advances_automatically = not self.include_payments
        sales_invoice.cost_center = self.station
        sales_invoice.update_stock = 1
        sales_invoice.set_posting_time = 1
        sales_invoice.posting_date = self.date
        sales_invoice.posting_time = self.time
        sales_invoice.custom_sales_id = self.name
        sales_invoice.taxes_and_charges = self.sales_taxes_and_charges
        sales_invoice.custom_employee = self.employee

        for item in self.items:
            sales_invoice.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "warehouse": self.store,
                "amount": item.amount,
                "cost_center": self.station,
            })

        # Append taxes to the sales invoice
        if self.sales_taxes_and_charges:
            taxes_and_charges_doc = frappe.get_doc("Sales Taxes and Charges Template", self.sales_taxes_and_charges)
            for tax in taxes_and_charges_doc.taxes:
                sales_invoice.append("taxes", {
                    "charge_type": tax.charge_type,
                    "account_head": tax.account_head,
                    "rate": tax.rate,
                    "tax_amount": tax.tax_amount,
                    "description": tax.description,
                    "cost_center": tax.cost_center,
                })

        if sales_invoice.items:
            sales_invoice.insert()
            sales_invoice.submit()
            frappe.msgprint(_("Sales Invoice created and submitted"))

            if self.include_payments:
                self.create_payment_entry(sales_invoice)

    def create_payment_entry(self, sales_invoice):
        mode_of_pay_doc = frappe.get_doc("Mode of Payment", self.mode_of_payment)
        default_account = next((account.default_account for account in mode_of_pay_doc.accounts if account.default_account), None)

        if not default_account:
            frappe.msgprint(_("No accounts found for mode of payment {0}".format(self.mode_of_payment)))
            return

        existing_payment_entry = frappe.db.exists("Payment Entry", {
            "party_type": "Customer",
            "party": self.customer,
            "custom_sales_id": self.name,
            "docstatus": 1
        })
        if existing_payment_entry:
            frappe.msgprint(_("Payment Entry already exists for invoice {0}".format(sales_invoice.name)))
            return

        outstanding_amount = sales_invoice.outstanding_amount
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.party_type = "Customer"
        payment_entry.payment_type = "Receive"
        payment_entry.posting_date = self.date
        payment_entry.party = self.customer
        payment_entry.paid_amount = outstanding_amount
        payment_entry.received_amount = outstanding_amount
        payment_entry.target_exchange_rate = 1.0
        payment_entry.paid_to = default_account
        payment_entry.paid_to_account_currency = frappe.db.get_value("Account", default_account, "account_currency")
        payment_entry.mode_of_payment = self.mode_of_payment
        payment_entry.custom_sales_id = self.name
        payment_entry.custom_employee = self.employee
        payment_entry.cost_center = self.station

        payment_entry.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": sales_invoice.name,
            "allocated_amount": outstanding_amount
        })

        try:
            payment_entry.insert()
            payment_entry.submit()
            frappe.db.commit()
            frappe.msgprint(_("Payments made for invoice {0}".format(sales_invoice.name)))
        except Exception as e:
            frappe.log_error(message=str(e), title="Payment Entry Creation Error")
            frappe.throw(_("Error in creating Payment Entry: {0}".format(str(e))))
