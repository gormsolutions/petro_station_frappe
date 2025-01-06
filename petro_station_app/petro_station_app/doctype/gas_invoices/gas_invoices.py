# Copyright (c) 2024, mututa paul and contributors
# For license information, please see license.txt

import frappe  # type: ignore
from frappe.model.document import Document
from frappe import _  # type: ignore

class GasInvoices(Document):
    def on_submit(self):
        if self.gas_empty_cylinders:
            if not self.store_for_empties:
                frappe.throw(_("Store For Empties"))
                
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
        stock_entry.custom_gas_sale_id = self.name
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

           

    # def create_payment_entry(self, sales_invoice):
    #     mode_of_pay_doc = frappe.get_doc("Mode of Payment", self.mode_of_payment)
    #     default_account = next((account.default_account for account in mode_of_pay_doc.accounts if account.default_account), None)

    #     if not default_account:
    #         frappe.msgprint(_("No accounts found for mode of payment {0}".format(self.mode_of_payment)))
    #         return

    #     existing_payment_entry = frappe.db.exists("Payment Entry", {
    #         "party_type": "Customer",
    #         "party": self.customer,
    #         "custom_gas_invice_id": self.name,
    #         "docstatus": 1
    #     })
    #     if existing_payment_entry:
    #         frappe.msgprint(_("Payment Entry already exists for invoice {0}".format(sales_invoice.name)))
    #         return

    #     outstanding_amount = sales_invoice.outstanding_amount
    #     payment_entry = frappe.new_doc("Payment Entry")
    #     payment_entry.party_type = "Customer"
    #     payment_entry.payment_type = "Receive"
    #     payment_entry.posting_date = self.date
    #     payment_entry.party = self.customer
    #     payment_entry.paid_amount = outstanding_amount
    #     payment_entry.received_amount = outstanding_amount
    #     payment_entry.target_exchange_rate = 1.0
    #     payment_entry.paid_to = default_account
    #     payment_entry.paid_to_account_currency = frappe.db.get_value("Account", default_account, "account_currency")
    #     payment_entry.mode_of_payment = self.mode_of_payment
    #     payment_entry.custom_gas_invice_id = self.name
    #     payment_entry.custom_employee = self.employee
    #     payment_entry.cost_center = self.station

    #     allocated_amount = min(self.grand_totals, outstanding_amount)
    #     payment_entry.append("references", {
    #         "reference_doctype": "Sales Invoice",
    #         "reference_name": sales_invoice.name,
    #         "allocated_amount": allocated_amount
    #     })

    #     try:
    #         payment_entry.insert()
    #         payment_entry.submit()
    #         frappe.db.commit()
    #         frappe.msgprint(_("Payments made for invoice {0}".format(sales_invoice.name)))
    #     except Exception as e:
    #         frappe.log_error(message=str(e), title="Payment Entry Creation Error")
    #         frappe.throw(_("Error in creating Payment Entry: {0}".format(str(e))))
    
    def create_payment_entry(self, sales_invoice):
        mode_of_pay_doc = frappe.get_doc("Mode of Payment", self.mode_of_payment)
        default_account = next((account.default_account for account in mode_of_pay_doc.accounts if account.default_account), None)

        if not default_account:
            frappe.msgprint(_("No accounts found for mode of payment {0}".format(self.mode_of_payment)))
            return
        
        # Fetch the total promotional amount
        promotional_amount = frappe.db.get_value("Journal Entry", 
                                             {"promotion_gas_id": self.name}, 
                                             "total_credit")

    # Calculate the remaining balance to be paid
        remaining_balance = sales_invoice.outstanding_amount - (promotional_amount or 0)

        if remaining_balance <= 0:
            frappe.msgprint(_("No remaining balance to create a Payment Entry."))
            return

    # Fetch the Receivable account
        receivable_account = frappe.db.get_value("Company", self.company, "default_receivable_account")
        if not receivable_account:
            frappe.throw(_("No default Receivable account found for the company."))

    # Create a new Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.party_type = "Customer"
        payment_entry.payment_type = "Receive"
        payment_entry.posting_date = self.date
        payment_entry.party = self.customer
        payment_entry.paid_amount = remaining_balance
        payment_entry.received_amount = remaining_balance
        payment_entry.target_exchange_rate = 1.0
        payment_entry.paid_to = default_account
        payment_entry.paid_to_account_currency = frappe.db.get_value("Account", default_account, "account_currency")
        payment_entry.mode_of_payment = self.mode_of_payment
        payment_entry.custom_gas_invice_id = self.name
        payment_entry.custom_employee = self.employee
        payment_entry.cost_center = self.station

    # Reference the Sales Invoice in Payment Entry
        payment_entry.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": sales_invoice.name,
        "total_amount": sales_invoice.grand_total,
        "outstanding_amount": sales_invoice.outstanding_amount,
        "allocated_amount": remaining_balance
    })

    # Save and submit the Payment Entry
        payment_entry.insert()
        payment_entry.submit()
        frappe.msgprint(_("Payment Entry for the remaining balance has been created and submitted."))

    def on_update(self):
        # Use a flag to prevent infinite recursion
        if not hasattr(self, "_from_on_update"):
            setattr(self, "_from_on_update", True)

            if self.items:
                # Gather existing entries in the gas_empty_cylinders table
                existing_item_codes = {cylinder.item_code for cylinder in self.gas_empty_cylinders}

                for item in self.items:
                    # Fetch the item details
                    refill_item = frappe.get_doc('Item', item.item_code)

                    # Debug: Log the item's custom_gas_stock_entry_name
                    frappe.log_error(
                        message=f"Processing item {item.item_code} with custom_gas_stock_entry_name: {refill_item.custom_gas_stock_entry_name}",
                        title="Debug Log"
                    )

                    # Check if the item's custom_gas_stock_entry_name is 'Refill'
                    if refill_item.custom_gas_stock_entry_name == 'Refill':
                        # Fetch the product bundle details for the item's name
                        product_bundle = frappe.get_doc('Product Bundle', item.item_code)

                        # Debug: Log the fetched Product Bundle details
                        frappe.log_error(
                            message=f"Fetched Product Bundle for item {item.item_code}: {product_bundle}",
                            title="Debug Log"
                        )

                        # Iterate through the Product Bundle's items
                        for bundle_item in product_bundle.items:
                            # Fetch the corresponding item details
                            bundle_item_details = frappe.get_doc('Item', bundle_item.item_code)

                            # Debug: Log the bundle item's custom_gas_stock_entry_name
                            frappe.log_error(
                                message=f"Processing bundle item {bundle_item.item_code} with custom_gas_stock_entry_name: {bundle_item_details.custom_gas_stock_entry_name}",
                                title="Debug Log"
                            )

                            # Check if the bundle item's custom_gas_stock_entry_name is 'Empties'
                            if bundle_item_details.custom_gas_stock_entry_name == 'Empties':
                                # Skip duplicates already in the child table
                                if bundle_item.item_code in existing_item_codes:
                                    # frappe.msgprint(
                                    #     _(f"Skipped {bundle_item.item_code} as it already exists in gas_empty_cylinders")
                                    # )
                                    continue

                                # Add to the gas_empty_cylinders child table
                                self.append("gas_empty_cylinders", {
                                    "item_code": bundle_item.item_code,
                                    "qty": item.qty,
                                    "uom": item.uom,
                                    "warehouse": self.store_for_empties
                                })

                                # Add the item to the set of existing item codes
                                existing_item_codes.add(bundle_item.item_code)

                                # Debug: Log successful append
                                frappe.log_error(
                                    message=f"Appended to gas_empty_cylinders: {bundle_item.item_code}, qty: {item.qty}, uom: {item.uom}, warehouse: {self.store_for_empties}",
                                    title="Debug Log"
                                )

            # Save the document to commit changes to the child table
            self.save(ignore_permissions=True)

            # Remove the flag after execution
            delattr(self, "_from_on_update")

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
        sales_invoice.custom_gas_invice_id = self.name
        sales_invoice.custom_employee = self.employee
        
        promotional_items = []
        total_amount = 0
        
        for item in self.items:
            # Fetch item details from Item doctype
            custom_on_promotion, custom_promotion_amount = frappe.get_value(
                "Item", 
                item.item_code, 
                ["custom_on_promotion", "custom_promotion_amount"]
            )
            
            sales_invoice.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "warehouse": self.store,
                "amount": item.amount,
                "cost_center": self.station,
            })
            
            total_amount += item.amount

            # Check if the item is promotional
            if custom_on_promotion == 1 and custom_promotion_amount:
                promotional_items.append({
                    "item_code": item.item_code,
                    "promotion_amount": custom_promotion_amount
                })

        if sales_invoice.items:
            sales_invoice.insert()
            sales_invoice.submit()
            frappe.msgprint(_("Sales Invoice created and submitted"))
            
            # Create a Journal Entry for promotional items
            if promotional_items:
                self.create_promotion_journal_entry(promotional_items, total_amount, sales_invoice.name)

            if self.include_payments:
                self.create_payment_entry(sales_invoice)

    def create_promotion_journal_entry(self, promotional_items, total_amount, sales_invoice_name):
        # Fetch default promotional account and mode of payment account from Promotional Settings
        promotional_accounts = frappe.get_all(
            "Promotional Settings",
            fields=["account", "mode_of_payment_account"],
            limit_page_length=1  # Limit to the first record
        )

        # Extract the first promotional account and mode of payment account
        promotional_account = promotional_accounts[0].get("account") if promotional_accounts else None
        # Throw an error if the promotional account is not set
        if not promotional_account:
            frappe.throw(_("No default promotional account found in Promotional Settings. Please configure it."))

        # Create a new Journal Entry
        journal_entry = frappe.new_doc("Journal Entry")
        journal_entry.voucher_type = "Journal Entry"
        journal_entry.company = self.company
        journal_entry.posting_date = self.date
        journal_entry.custom_employee = self.employee
        journal_entry.promotion_gas_id = self.name
        
        total_debit = 0
        total_credit = 0
        
        # Calculate total promotion amount
        total_promotion_amount = sum(item.get('promotion_amount') for item in promotional_items)

        
        # Debit Entry for 1310 - Debtors - SE account (Grand Total of the invoice)
        journal_entry.append("accounts", {
            "account": "1310 - Debtors - SE",
            "reference_type":"Sales Invoice",
            "reference_name":sales_invoice_name,
            "party_type": "Customer",
            "party": self.customer,
            "description": f"Invoice for {self.name}",
            "debit_in_account_currency": 0,
            "credit_in_account_currency": total_promotion_amount,
            "cost_center": self.station,
        })
        total_debit += total_amount

        
        # Credit Entry for the promotional account
        if total_promotion_amount > 0:
            journal_entry.append("accounts", {
                "account": promotional_account,
                "party_type": "Customer",
                "party": self.customer,
                "description": f"Promotion for {self.name}",
                "debit_in_account_currency": total_promotion_amount,
                "credit_in_account_currency": 0,
                "cost_center": self.station,
            })
            total_credit += total_promotion_amount

        # Save and submit the Journal Entry
        if journal_entry.accounts:
            journal_entry.insert()
            journal_entry.submit()
            frappe.db.commit()
            frappe.msgprint(_("Journal Entry for promotional items created and submitted."))
        else:
            frappe.throw(_("Journal Entry could not be created as no valid promotional items were found."))
