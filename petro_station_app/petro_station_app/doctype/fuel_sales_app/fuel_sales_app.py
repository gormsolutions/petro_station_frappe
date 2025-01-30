from frappe.model.document import Document # type: ignore
import frappe # type: ignore
from frappe import _ # type: ignore

class FuelSalesApp(Document):

    # def on_submit(self):
    #     # Filter fuel items from the item list
    #     fuel_items = [item for item in self.items if frappe.get_value("Item", item.item_code, "item_group") == "Fuel"]

    #     if fuel_items:
    #         # Create a Stock Transfer for fuel items
    #         company_abbr = frappe.get_value("Company", self.company, "abbr")
    #         stock_entry = frappe.new_doc("Stock Entry")
    #         stock_entry.stock_entry_type = "Material Transfer"
    #         stock_entry.set_posting_time = 1
    #         stock_entry.posting_time = self.time
    #         stock_entry.posting_date = self.date
    #         stock_entry.custom_employee = self.employee
    #         stock_entry.custom_cash_sales_app = self.name

    #         for item in fuel_items:
    #             source_warehouse = item.warehouse
    #             if f" - {company_abbr}" in source_warehouse:
    #                 source_warehouse_strip = source_warehouse[:-len(f" - {company_abbr}")].strip()
    #             else:
    #                 source_warehouse_strip = source_warehouse
    #             warehouse = frappe.get_all("Warehouse", filters={"warehouse_name": source_warehouse_strip},
    #                                        fields=["default_in_transit_warehouse", "parent_warehouse"])
    #             if warehouse:
    #                 in_transit_warehouse = warehouse[0].get("default_in_transit_warehouse")
    #                 if not in_transit_warehouse:
    #                     frappe.throw(_("Transit warehouse not set in Warehouse"))
    #                 stock_entry.append("items", {
    #                     "item_code": item.item_code,
    #                     "qty": item.qty,
    #                     "uom": item.uom,
    #                     "s_warehouse": in_transit_warehouse,
    #                     "t_warehouse": source_warehouse
               
    #                 })

    #         stock_entry.insert()
    #         stock_entry.submit()
    #         frappe.db.commit()
    #         frappe.msgprint(_("Tank to Pump transfer successfully transferred to the Client"))

    #     # Check if a Sales Invoice has already been created  price_list
    #     if not self.sales_invoice_created:
    #         sales_invoice = frappe.new_doc("Sales Invoice")
    #         sales_invoice.customer = self.customer
    #         sales_invoice.discount_amount = self.additional_discount_amount
    #         sales_invoice.due_date = self.due_date
    #         sales_invoice.allocate_advances_automatically = 0 if self.include_payments == 1 else 1
    #         sales_invoice.cost_center = self.station 
    #         sales_invoice.update_stock = 1
    #         sales_invoice.set_posting_time = 1
    #         sales_invoice.selling_price_list = self.price_list
    #         sales_invoice.posting_date = self.date
    #         sales_invoice.posting_time = self.time
    #         sales_invoice.additional_discount_account = "5125 - Discounts on Fuel - SE"
    #         sales_invoice.custom_invoice_no = self.invoice_no
    #         sales_invoice.custom_fuel_sales_app_id = self.name
    #         sales_invoice.custom_employee = self.employee
    #         remarks = ""
    #         for item in self.items:
    #             sales_invoice.append("items", {
    #                 "item_code": item.item_code,
    #                 "qty": item.qty,
    #                 "rate": item.rate,
    #                 "warehouse": item.warehouse,
    #                 "amount": item.amount,
    #                 "cost_center":self.station,
    #                 "custom_vehicle_plates": item.number_plate
    #             })
    #             # Append each item's details to the remarks string
    #             if item.number_plate:
    #                 remarks += f"Item: {item.item_code}, Quantity: {item.qty}, Amount: {item.amount}, Vehicle Plate: {item.number_plate}\n"
    #          # Set the accumulated remarks in the Sales Invoice
    #         sales_invoice.remarks = remarks
               
    #         if sales_invoice.items:
    #             sales_invoice.insert()
    #             sales_invoice.submit()
    #             self.sales_invoice_created = sales_invoice.name
    #             self.net_total = sales_invoice.net_total
    #             frappe.msgprint(_("Sales Invoice created and submitted"))

    #             # Calculate net total
    #             # net_total = sum(item.net_amount for item in sales_invoice.items)
    #             outstanding_amount = sales_invoice.outstanding_amount

    #             # Create Payment Entry
    #             if self.include_payments:
    #                 pos_profile = self.items[0].pos_profile if self.items else None
    #                 payment_methods = frappe.get_all("POS Payment Method", filters={"parent": pos_profile},
    #                                                  fields=["mode_of_payment"])
    #                 for payment_method in payment_methods:
    #                     mode_of_payment = payment_method.mode_of_payment
    #                     mode_of_pay_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
    #                     default_account = mode_of_pay_doc.accounts[0].default_account
    #                     currency = frappe.db.get_value("Account", default_account, "account_currency")
    #                     payment_entry = frappe.new_doc("Payment Entry")
    #                     payment_entry.party_type = "Customer"
    #                     payment_entry.payment_type = "Receive"
    #                     payment_entry.posting_date = self.date
    #                     payment_entry.party = self.customer
    #                     payment_entry.paid_amount = outstanding_amount
    #                     payment_entry.received_amount = outstanding_amount
    #                     payment_entry.target_exchange_rate = 1.0
    #                     payment_entry.paid_to = default_account
    #                     payment_entry.paid_to_account_currency = currency
    #                     payment_entry.mode_of_payment = mode_of_payment
    #                     payment_entry.custom_fuel_sales_app_id = self.name
    #                     payment_entry.custom_employee = self.employee
    #                     payment_entry.cost_center = self.station 

    #                     # Ensure allocated amount does not exceed the outstanding amount
    #                     outstanding_amount = sales_invoice.outstanding_amount
    #                     # allocated_amount = min(net_total, outstanding_amount)
    #                     allocated_amount = outstanding_amount
    #                     payment_entry.append("references", {
    #                         "reference_doctype": "Sales Invoice",
    #                         "reference_name": sales_invoice.name,
    #                         "allocated_amount": allocated_amount
    #                     })

    #                     payment_entry.insert()
    #                     payment_entry.submit()
    #                     frappe.db.commit()
    #                     frappe.msgprint(_(f"Payments Made for invoice {sales_invoice.name}"))

    #                 # self.db_set("sales_invoice_created", sales_invoice.name)
    
    def on_submit(self):
        try:
            # Step 1: Filter fuel items from the item list
            fuel_items = [item for item in self.items if frappe.get_value("Item", item.item_code, "item_group") == "Fuel"]

            # Step 2: Create Stock Entry for fuel items (if any)
            if fuel_items:
                company_abbr = frappe.get_value("Company", self.company, "abbr")
                stock_entry = frappe.new_doc("Stock Entry")
                stock_entry.stock_entry_type = "Material Transfer"
                stock_entry.set_posting_time = 1
                stock_entry.posting_time = self.time
                stock_entry.posting_date = self.date
                stock_entry.custom_employee = self.employee
                stock_entry.custom_cash_sales_app = self.name

                for item in fuel_items:
                    source_warehouse = item.warehouse
                    source_warehouse_strip = (
                        source_warehouse[:-len(f" - {company_abbr}")].strip()
                        if f" - {company_abbr}" in source_warehouse else source_warehouse
                    )
                    warehouse = frappe.get_all("Warehouse", filters={"warehouse_name": source_warehouse_strip},
                                           fields=["default_in_transit_warehouse", "parent_warehouse"])
                    if warehouse:
                        in_transit_warehouse = warehouse[0].get("default_in_transit_warehouse")
                        if not in_transit_warehouse:
                            frappe.throw(_("Transit warehouse not set in Warehouse"))
                        stock_entry.append("items", {
                            "item_code": item.item_code,
                            "qty": item.qty,
                            "uom": item.uom,
                            "s_warehouse": in_transit_warehouse,
                            "t_warehouse": source_warehouse
                        })

                stock_entry.insert()
                stock_entry.submit()

            # Step 3: Create Sales Invoice (if not already created)
            if not self.sales_invoice_created:
                sales_invoice = frappe.new_doc("Sales Invoice")
                sales_invoice.customer = self.customer
                sales_invoice.discount_amount = self.additional_discount_amount
                sales_invoice.due_date = self.due_date
                sales_invoice.allocate_advances_automatically = 0 if self.include_payments == 1 else 1
                sales_invoice.cost_center = self.station
                sales_invoice.update_stock = 1
                sales_invoice.set_posting_time = 1
                sales_invoice.selling_price_list = self.price_list
                sales_invoice.posting_date = self.date
                sales_invoice.posting_time = self.time
                sales_invoice.additional_discount_account = "5125 - Discounts on Fuel - SE"
                sales_invoice.custom_invoice_no = self.invoice_no
                sales_invoice.custom_fuel_sales_app_id = self.name
                sales_invoice.custom_employee = self.employee

                remarks = ""
                for item in self.items:
                    sales_invoice.append("items", {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "rate": item.rate,
                    "warehouse": item.warehouse,
                    "amount": item.amount,
                    "cost_center": self.station,
                    "custom_vehicle_plates": item.number_plate
                    })
                    if item.number_plate:
                        remarks += f"Item: {item.item_code}, Quantity: {item.qty}, Amount: {item.amount}, Vehicle Plate: {item.number_plate}\n"
                sales_invoice.remarks = remarks

                sales_invoice.insert()
                sales_invoice.submit()
                self.sales_invoice_created = sales_invoice.name
                self.net_total = sales_invoice.net_total

            # Step 4: Create Payment Entries (if applicable)
            if self.include_payments:
                outstanding_amount = frappe.get_value("Sales Invoice", sales_invoice.name, "outstanding_amount")
                pos_profile = self.items[0].pos_profile if self.items else None
                payment_methods = frappe.get_all("POS Payment Method", filters={"parent": pos_profile},
                                             fields=["mode_of_payment"])
                for payment_method in payment_methods:
                    mode_of_payment = payment_method.mode_of_payment
                    mode_of_pay_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
                    default_account = mode_of_pay_doc.accounts[0].default_account
                    currency = frappe.db.get_value("Account", default_account, "account_currency")
                    payment_entry = frappe.new_doc("Payment Entry")
                    payment_entry.party_type = "Customer"
                    payment_entry.payment_type = "Receive"
                    payment_entry.posting_date = self.date
                    payment_entry.party = self.customer
                    payment_entry.paid_amount = outstanding_amount
                    payment_entry.received_amount = outstanding_amount
                    payment_entry.target_exchange_rate = 1.0
                    payment_entry.paid_to = default_account
                    payment_entry.paid_to_account_currency = currency
                    payment_entry.mode_of_payment = mode_of_payment
                    payment_entry.custom_fuel_sales_app_id = self.name
                    payment_entry.custom_employee = self.employee
                    payment_entry.cost_center = self.station
                    payment_entry.append("references", {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": sales_invoice.name,
                    "allocated_amount": outstanding_amount
                    })
                    payment_entry.insert()
                    payment_entry.submit()

            # Step 5: Commit only if all operations are successful
            frappe.db.commit()
            frappe.msgprint(_("All operations completed successfully"))
        except Exception as e:
            # Rollback in case of any errors
            frappe.db.rollback()
            frappe.throw(_("An error occurred during submission: {0}").format(str(e)))

    def before_save(self):
        if self.date and self.station:
            if self.items:
                for item in self.items:
                    pos_profile = frappe.get_doc('POS Profile', item.pos_profile)
                    if pos_profile.custom_fuel != item.item_code:
                        frappe.throw(_(f"{item.item_code} Selected in Fuel Sales Item should match with the selected '{item.pos_profile}' Pump => {pos_profile.custom_fuel}"))
                        
                    if item.qty > item.actual_qty:
                        exceeding_qty = item.qty - item.actual_qty
                        frappe.throw(
                            f"NO NO NO '{item.item_code}' qty is going beyond what is in the '{item.warehouse}'. Exceeding by {exceeding_qty:.3f}."
                        )

                # Check if the warehouse (in self.items) matches pump_or_tank in Station Shift Management Item
                    existing_doc = frappe.db.sql(
                    """
                    SELECT parent 
                    FROM `tabStation Shift Management item` AS shift_item
                    JOIN `tabStation Shift Management` AS shift_doc
                    ON shift_item.parent = shift_doc.name
                    WHERE 
                        shift_doc.from_date = %(date)s 
                        AND shift_doc.employee = %(employee)s 
                        AND shift_doc.shift = %(shift)s
                        AND shift_item.pump_or_tank = %(warehouse)s
                    """,
                    {
                        'date': self.date,            # self.date maps to shift_doc.from_date
                        'employee': self.employee,
                        'shift': self.shift,
                        'warehouse': item.warehouse   # item.warehouse is checked against pump_or_tank
                    }
                )

                # If no matching record is found
                    if not existing_doc:
                        frappe.throw(
                        f"The warehouse '{item.warehouse}' is not associated with a shift document for {self.shift} on {self.date}."
                    )

