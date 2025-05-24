from frappe.model.document import Document
import frappe
from frappe import _

class CreditSalesApp(Document):
    def on_submit(self):
        try:
            # 1) General validation
            self.validate_before_save()

            # 2) Create & submit Stock Entry for fuel items, keep the doc in-memory
            stock_entry = self.create_fuel_stock_transfer()

            # 3) Build Delivery Note off that exact Stock Entry
            dn = self.create_delivery_note(stock_entry)

            # 4) Create Sales Invoice
            self.create_sales_invoice(dn)

            frappe.db.commit()
            frappe.msgprint(_("All operations completed successfully"))

        except Exception as e:
            frappe.db.rollback()
            frappe.throw(_("An error occurred during submission: {0}").format(str(e)))

    def validate_before_save(self):
        """Validate before saving the document."""
        if self.date and self.station and self.items and len(self.items) > 0:
            for item in self.items:
                # Fuel item must match POS Profile
                pos_profile = frappe.get_doc('POS Profile', item.pos_profile)
                if pos_profile.custom_fuel != item.item_code:
                    frappe.throw(_(
                        f"{item.item_code} selected in Fuel Sales Item should match "
                        f"the selected '{item.pos_profile}' Pump => {pos_profile.custom_fuel}"
                    ))

                # Warehouse must be linked to shift OR to mobile warehouse
                exists = frappe.db.sql("""
                SELECT parent
                FROM `tabStation Shift Management item` shift_item
                JOIN `tabStation Shift Management` shift_doc
                  ON shift_item.parent = shift_doc.name
                WHERE shift_doc.from_date = %(date)s
                  AND shift_doc.employee = %(employee)s
                  AND shift_doc.shift = %(shift)s
                  AND shift_item.pump_or_tank = %(warehouse)s
            """, {
                'date': self.date,
                'employee': self.employee,
                'shift': self.shift,
                'warehouse': item.warehouse
                })

                exists_mobile = frappe.db.sql("""
                SELECT parent
                FROM `tabMobile Warehouse Items` shift_item
                JOIN `tabStation Shift Management` shift_doc
                  ON shift_item.parent = shift_doc.name
                WHERE shift_doc.from_date = %(date)s
                  AND shift_doc.employee = %(employee)s
                  AND shift_doc.shift = %(shift)s
                  AND shift_item.mw_plate_number = %(warehouse)s
            """, {
                'date': self.date,
                'employee': self.employee,
                'shift': self.shift,
                'warehouse': item.warehouse
                })

                if not exists and not exists_mobile:
                    frappe.throw(_(
                    f"The warehouse '{item.warehouse}' is not associated with any shift "
                    f"document (regular or mobile) for {self.shift} on {self.date}."
                    ))


    def create_fuel_stock_transfer(self):
        """Create & submit Stock Entry for all Fuel items, return the Stock Entry doc."""
        # filter only Fuel items
        fuel_items = [
            row for row in self.items
            if frappe.get_value("Item", row.item_code, "item_group") == "Fuel"
        ]
        if not fuel_items:
            return None

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.set_posting_time = 1
        se.posting_date = self.date
        se.posting_time = self.time
        se.custom_employee = self.employee
        se.custom_credit_sales_app = self.name
        se.custom_cost_center = self.station
        se.location = self.location
        se.branch = self.branch

        for row in fuel_items:
            # derive in-transit warehouse
            base_wh = row.warehouse.rsplit(" - ", 1)[0]
            wh = frappe.get_value("Warehouse",
                                  {"warehouse_name": base_wh},
                                  ["default_in_transit_warehouse"], as_dict=1)
            if not wh or not wh.default_in_transit_warehouse:
                frappe.throw(_("Transit warehouse not set for {0}").format(base_wh))

            se.append("items", {
                "item_code": row.item_code,
                "qty": row.qty,
                "uom": row.uom,
                # "s_warehouse": wh.default_in_transit_warehouse,
                "s_warehouse": row.fuel_tank,
                "t_warehouse": row.warehouse
            })

        se.insert()
        se.submit()
        return se

    def create_delivery_note(self, stock_entry):
        """Create & submit a Delivery Note, pulling valuation rates from that Stock Entry."""
        if not stock_entry:
            frappe.throw(_("No fuel Stock Entry was created, so Delivery Note cannot be built."))

        dn = frappe.new_doc("Delivery Note")
        dn.company = self.company
        dn.customer = self.customer
        dn.posting_date = self.date
        dn.posting_time = getattr(self, "time", None)
        dn.location = self.location
        dn.branch = self.branch
        dn.cost_center = self.station

        for row in self.items:
            # fetch the SLE line that belongs to our stock_entry
            sle = frappe.get_all(
                "Stock Ledger Entry",
                filters={
                    "voucher_no": stock_entry.name,
                    "item_code": row.item_code,
                    "warehouse": row.warehouse,
                    "docstatus": 1
                },
                fields=["valuation_rate"],
                order_by="creation desc",
                limit_page_length=1
            ) or []

            rate_to_use = sle[0].valuation_rate if sle else row.rate

            dn.append("items", {
                "item_code": row.item_code,
                "qty": row.qty,
                "uom": row.uom,
                "warehouse": row.warehouse,
                "rate": rate_to_use
            })

        if not dn.items:
            frappe.throw(_("No items found to create Delivery Note."))

        dn.insert()
        # dn.submit()
        frappe.msgprint(_("Delivery Note {0} created.").format(dn.name))
        return dn

    def create_sales_invoice(self, dn):
        """Create & submit the Sales Invoice, linking back to the DN."""
        if not dn:
            frappe.throw(_("Delivery Note is required to create Sales Invoice."))

        if not getattr(self, "sales_invoice_created", None):
            inv = frappe.new_doc("Sales Invoice")
            inv.customer = self.customer
            inv.discount_amount = self.additional_discount_amount
            inv.due_date = self.due_date
            inv.allocate_advances_automatically = 0
            inv.cost_center = self.station
            inv.update_stock = 1
            inv.set_posting_time = 1
            inv.selling_price_list = self.price_list
            inv.posting_date = self.date
            inv.posting_time = self.time
            inv.remarks = self.remarks
            inv.location = self.location
            inv.branch = self.branch
            inv.custom_product_supplier = self.custom_product_supplier
            inv.additional_discount_account = "5371 - Discount Allowed - AO&GN"
            inv.custom_invoice_no = self.invoice_no
            inv.custom_credit_sales_app = self.name
            inv.custom_employee = self.employee

            remarks = self.remarks or ""
            for row in self.items:
                inv.append("items", {
                    "item_code": row.item_code,
                    "qty": row.qty,
                    "rate": row.rate,
                    "warehouse": row.warehouse,
                    "amount": row.amount,
                    "cost_center": self.station,
                    "sales_order": self.sales_order_number,
                    "custom_vehicle_plates": row.number_plate
                })
                if row.number_plate:
                    remarks += (
                        f"\nItem: {row.item_code}, Qty: {row.qty}, Amount: {row.amount}, "
                        f"Plate: {row.number_plate}"
                    )
            inv.remarks = remarks

            inv.insert()
            inv.submit()

            # link back the DN on each invoice item
            for inv_item in inv.items:
                frappe.db.set_value("Sales Invoice Item", inv_item.name,
                                    "delivery_note", dn.name)

            frappe.db.commit()
            frappe.msgprint(_("Sales Invoice {0} created.").format(inv.name))

            self.sales_invoice_created = inv.name
            self.net_total = inv.net_total
        else:
            inv = frappe.get_doc("Sales Invoice", self.sales_invoice_created)

        return inv
