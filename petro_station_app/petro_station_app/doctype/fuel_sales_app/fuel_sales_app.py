from frappe.model.document import Document  # type: ignore
import frappe  # type: ignore
from frappe import _  # type: ignore


class FuelSalesApp(Document):
    def on_submit(self):
        try:
            
            # Handle stock entry (only for fuel items)
            fuel_items = [
                item for item in self.items
                if frappe.get_value("Item", item.item_code, "item_group") == "Fuel"
            ]

            if fuel_items:
                company_abbr = frappe.get_value("Company", self.company, "abbr")
                stock_entry = frappe.new_doc("Stock Entry")
                stock_entry.stock_entry_type = "Material Transfer"
                stock_entry.set_posting_time = 1
                stock_entry.posting_time = self.time
                stock_entry.posting_date = self.date
                stock_entry.custom_employee = self.employee
                stock_entry.custom_cash_sales_app = self.name
                stock_entry.custom_cost_center = self.station
                stock_entry.location = self.location
                stock_entry.branch = self.branch

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
                            # "s_warehouse": in_transit_warehouse,
                            "s_warehouse": item.fuel_tank,
                            "t_warehouse": source_warehouse
                        })

                stock_entry.insert()
                stock_entry.submit()

            invoice = None

            if not self.sales_invoice_created:
                invoice = frappe.new_doc("Sales Invoice")
                invoice.customer = self.customer
                invoice.discount_amount = self.additional_discount_amount
                invoice.due_date = self.due_date
                invoice.allocate_advances_automatically = 0 if self.select_other_modes_of_payment == 1 else 1
                invoice.cost_center = self.station
                invoice.update_stock = 1
                invoice.set_posting_time = 1
                invoice.selling_price_list = self.price_list
                invoice.posting_date = self.date
                invoice.posting_time = self.time
                invoice.remarks = self.remarks
                invoice.location = self.location
                invoice.branch = self.branch
                invoice.custom_product_supplier = self.custom_product_supplier
                invoice.additional_discount_account = "5371 - Discount Allowed - AO&GN"
                invoice.custom_invoice_no = self.invoice_no
                invoice.custom_fuel_sales_app_id = self.name
                invoice.custom_employee = self.employee

                remarks = self.remarks
                for item in self.items:
                    invoice.append("items", {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "rate": item.rate,
                        "warehouse": item.warehouse,
                        "amount": item.amount,
                        "cost_center": self.station,
                        "sales_order": self.sales_order_number,
                        "custom_vehicle_plates": item.number_plate
                    })
                    if item.number_plate:
                        remarks += f"Item: {item.item_code}, Quantity: {item.qty}, Amount: {item.amount}, Vehicle Plate: {item.number_plate}\n"
                invoice.remarks = remarks
                invoice.insert()
                invoice.submit()

                self.sales_invoice_created = invoice.name
                self.net_total = invoice.net_total
            else:
                invoice = frappe.get_doc("Sales Invoice", self.sales_invoice_created)


            # Create payment entries if configured
            # if self.include_payments:
            #     self.create_pos_payments(invoice)

            # Create other payments if checkbox is set
            if invoice and self.select_other_modes_of_payment:
                self.create_other_payments(invoice)

            # Create delivery note (optional)
            if invoice:
                self.create_delivery_note(invoice)

            frappe.db.commit()
            frappe.msgprint(_("All operations completed successfully"))

        except Exception as e:
            frappe.db.rollback()
            frappe.throw(_("An error occurred during submission: {0}").format(str(e)))

    def before_save(self):
        if self.date and self.station:
            if self.items:
                for item in self.items:
                    pos_profile = frappe.get_doc('POS Profile', item.pos_profile)
                    if pos_profile.custom_fuel != item.item_code:
                        frappe.throw(_(
                            f"{item.item_code} selected in Fuel Sales Item should match the selected '{item.pos_profile}' Pump => {pos_profile.custom_fuel}"
                        ))

                    # Check in both child tables; proceed if found in either
                    exists_in_station_item = frappe.db.exists(
                        {
                            "doctype": "Station Shift Management item",
                            "pump_or_tank": item.warehouse,
                            "parent": [
                                "in",
                                frappe.db.get_all(
                                    "Station Shift Management",
                                    filters={
                                        "from_date": self.date,
                                        "employee": self.employee,
                                        "shift": self.shift
                                    },
                                    pluck="name"
                                )
                            ]
                        }
                    )

                    exists_in_mobile_items = frappe.db.exists(
                        {
                            "doctype": "Mobile Warehouse Items",
                            "mw_plate_number": item.warehouse,
                            "parent": [
                                "in",
                                frappe.db.get_all(
                                    "Station Shift Management",
                                    filters={
                                        "from_date": self.date,
                                        "employee": self.employee,
                                        "shift": self.shift
                                    },
                                    pluck="name"
                                )
                            ]
                        }
                    )

                    if not (exists_in_station_item or exists_in_mobile_items):
                        frappe.throw(_(
                            f"The warehouse '{item.warehouse}' is not associated with a shift document for {self.shift} on {self.date}."
                        ))

    def create_pos_payments(self, sales_invoice):
        net_total = sum(item.net_amount for item in sales_invoice.items)
        pos_profile = self.items[0].pos_profile if self.items else None

        methods = frappe.get_all(
            "POS Payment Method",
            filters={"parent": pos_profile},
            fields=["mode_of_payment"]
        )

        for m in methods:
            mop = m.mode_of_payment
            mop_doc = frappe.get_doc("Mode of Payment", mop)
            default_acc = mop_doc.accounts[0].default_account
            currency = frappe.db.get_value("Account", default_acc, "account_currency")

            pe = frappe.new_doc("Payment Entry")
            pe.payment_type = "Receive"
            pe.party_type = "Customer"
            pe.party = self.customer
            pe.posting_date = self.date
            pe.posting_time = self.time
            pe.company = self.company
            pe.custom_employee = self.employee
            pe.mode_of_payment = mop
            pe.paid_to = default_acc
            pe.paid_to_account_currency = currency
            pe.paid_amount = net_total
            pe.received_amount = net_total
            pe.target_exchange_rate = 1.0
            pe.custom_fuel_sales_app_id = self.name
            pe.cost_center = self.station
            pe.location = self.location
            pe.branch = self.branch

            outstanding = sales_invoice.outstanding_amount
            allocate = min(net_total, outstanding)
            pe.append("references", {
                "reference_doctype": "Sales Invoice",
                "reference_name": sales_invoice.name,
                "allocated_amount": allocate
            })

            pe.insert()
            pe.submit()
            frappe.db.commit()
            frappe.msgprint(_("POS payment of {0} via {1}").format(allocate, mop))
            
            break  # Only use first available mode of payment
        # Handle employee loss recovery
        if sales_invoice.outstanding_amount > 0:
            # Check if the invoice has a loss employee
            loss_amount = sales_invoice.outstanding_amount
            if loss_amount > 0:
                je = frappe.new_doc("Journal Entry")
                je.voucher_type = "Journal Entry"
                je.posting_date = self.date
                je.custom_cost_center = self.station
                je.custom_employee = self.employee
                je.custom_fuel_sales_app_id = self.name
                je.company = self.company
                je.remark = f"Loss on Sales Invoice {sales_invoice.name} to be recovered from {sales_invoice.custom_employee}"

                # Debit Loss on Sales account
                je.append("accounts", {
                    "account": "1311 - Employee Receivable (Shortage from Sales) - AO&GN",  # Replace with actual expense account if needed
                    "debit_in_account_currency": loss_amount,
                    "reference_type": "Sales Invoice",
                    "party_type": "Customer",
                    "party": sales_invoice.customer,
                    "reference_name": sales_invoice.name,
                    'location': self.location,
                    'cost_center': self.station,
                    'branch': self.branch
                })

                # Credit Employee Recoverable account
                je.append("accounts", {
                    "account": "1305 - Trade Debtors - AO&GN",  # Replace with your receivable account
                    "credit_in_account_currency": loss_amount,
                    "party_type": "Employee",
                    "party": sales_invoice.custom_employee,
                    'location': self.location,
                    'cost_center': self.station,
                    'branch': self.branch
                })

                je.save()
                je.submit()
                frappe.msgprint(f"Loss of {loss_amount} recorded for employee {sales_invoice.custom_employee}")


    def create_other_payments(self, sales_invoice):
        net_total = sum(item.net_amount for item in sales_invoice.items)
        er = frappe.db.get_value(
            "Currency Exchange",
            {
                "from_currency": sales_invoice.currency,
                "to_currency": frappe.defaults.get_global_default("default_currency")
            },
            "exchange_rate"
        ) or 1.0

        total_allocated = 0.0
        outstanding = sales_invoice.outstanding_amount

        for mode in self.payments:
            default_acc = frappe.db.get_value(
                "Mode of Payment Account",
                {"parent": mode.mode_of_payment, "company": self.company},
                "default_account"
            )
            if not default_acc:
                frappe.throw(_("No default account for {0} in {1}").format(mode.mode_of_payment, self.company))

            curr = frappe.db.get_value("Account", default_acc, "account_currency")

            allocate = min(mode.amount, outstanding)
            if allocate <= 0:
                continue  # Skip if nothing to allocate

            pe = frappe.new_doc("Payment Entry")
            pe.payment_type = "Receive"
            pe.party_type = "Customer"
            pe.party = self.customer
            pe.posting_date = frappe.utils.nowdate()
            pe.company = self.company
            pe.mode_of_payment = mode.mode_of_payment
            pe.custom_employee = self.employee
            pe.paid_to = default_acc
            pe.paid_to_account_currency = curr
            pe.paid_amount = allocate
            pe.received_amount = allocate
            pe.target_exchange_rate = er
            pe.custom_payment_id = self.name
            pe.reference_no = mode.transaction_id
            pe.reference_date = self.date
            pe.location = self.location
            pe.branch = self.branch
            pe.cost_center = self.station

            pe.append("references", {
                "reference_doctype": "Sales Invoice",
                "reference_name": sales_invoice.name,
                "allocated_amount": allocate
            })

            pe.insert()
            pe.submit()
            frappe.db.commit()
            frappe.msgprint(_("Other payment of {0} via {1}").format(allocate, mode.mode_of_payment))

            total_allocated += allocate
            outstanding -= allocate

            if outstanding <= 0:
                break  # Invoice fully paid, stop further payments

        # Handle employee loss recovery if some amount is unpaid
        if outstanding > 0:
            loss_amount = outstanding
            employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Journal Entry"
            je.posting_date = self.date
            je.custom_employee_loss = 1
            je.custom_cost_center = self.station
            je.custom_employee = self.employee
            je.custom_employee_name = employee_name
            je.custom_fuel_sales_app_id = self.name
            je.company = self.company
            je.remark = f"Loss on Sales Invoice {sales_invoice.name} to be recovered from {sales_invoice.custom_employee}"

            # Debit Loss on Sales account
            je.append("accounts", {
                "account": "1322 - Employee Receivable (Shortage from Sales) - AO&GN",  # Replace if needed
                "debit_in_account_currency": loss_amount,
                "party_type": "Employee",
                "party": sales_invoice.custom_employee,
                'location': self.location,
                'cost_center': self.station,
                'branch': self.branch
            })

            # Credit Customer Receivable (offset account)
            je.append("accounts", {
                "account": "1305 - Trade Debtors - AO&GN",  # Make sure this is a Customer receivable account
                "credit_in_account_currency": loss_amount,
                "party_type": "Customer",
                "reference_type": "Sales Invoice",
                "reference_name": sales_invoice.name,
                "party": sales_invoice.customer,
                'location': self.location,
                'cost_center': self.station,
                'branch': self.branch
            })

            je.save()
            je.submit()
            frappe.msgprint(f"Loss of {loss_amount} recorded for employee {sales_invoice.custom_employee}")



    def create_delivery_note(self, sales_invoice):
        dn = frappe.new_doc("Delivery Note")
        dn.company = sales_invoice.company
        dn.customer = sales_invoice.customer
        dn.posting_date = sales_invoice.posting_date
        dn.location = self.location
        dn.branch = self.branch
        dn.cost_center = self.station
        dn.posting_time = getattr(sales_invoice, "posting_time", None)

        for row in sales_invoice.items:
            sle = frappe.get_all(
                "Stock Ledger Entry",
                filters={"item_code": row.item_code, "warehouse": row.warehouse},
                fields=["valuation_rate"],
                order_by="posting_date desc, posting_time desc",
                limit_page_length=1
            )
            valuation_rate = sle[0].valuation_rate if sle else row.rate

            dn.append("items", {
                "item_code": row.item_code,
                "qty": row.qty,
                "uom": row.uom,
                "warehouse": row.warehouse,
                "rate": valuation_rate
            })

        if dn.items:
            dn.insert()
            # dn.submit()
            for row in sales_invoice.items:
                frappe.db.set_value("Sales Invoice Item", row.name, "delivery_note", dn.name)
            frappe.db.commit()
            frappe.msgprint(_("Delivery Note {0} created with valuation and linked to invoice items".format(dn.name)))
