# Copyright (c) 2024, mututa paul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe  # type: ignore
from frappe import _  # type: ignore


class GasCreditSales(Document):
    def on_submit(self):
        # self.create_stock_entry("Material Issue", "custom_gas_sale_id", "Empty cylinders sold successfully", self.items)
        self.create_sales_invoice()
        self.create_stock_entry("Material Receipt", "custom_gas_sales_id", "Empty cylinders received successfully", self.gas_empty_cylinders)

    def create_stock_entry(self, stock_entry_type, gas_sale_id_field, success_message, items):
        if not items:
            return

        existing_entry = frappe.db.exists("Stock Entry", {
            gas_sale_id_field: self.name,
            "stock_entry_type": stock_entry_type,
            "docstatus": 1
        })
        if existing_entry:
            frappe.msgprint(_(f"Stock Entry for {success_message.lower()} already exists"))
            return

        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = stock_entry_type
        stock_entry.set_posting_time = 1
        stock_entry.posting_time = self.time
        stock_entry.posting_date = self.date
        stock_entry.custom_employee = self.employee
        stock_entry.custom_gas_credit_invice_id = self.name
        stock_entry.cost_center = self.station

        for item in items:
            stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "cost_center": self.station,
                "t_warehouse": item.warehouse,
            })

        stock_entry.insert()
        stock_entry.submit()
        frappe.msgprint(_(success_message))

    def create_sales_invoice(self):
        existing_sales_invoice = frappe.db.exists("Sales Invoice", {
            "custom_gas_invice_id": self.name,
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
        sales_invoice.custom_gas_credit_invice_id = self.name
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

        if sales_invoice.items:
            sales_invoice.insert()
            sales_invoice.submit()
            frappe.msgprint(_("Sales Invoice created and submitted"))

