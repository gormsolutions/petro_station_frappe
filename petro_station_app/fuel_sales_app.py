import frappe
from frappe import _

# -----------------------------
# STEP 1: STOCK ENTRY
# -----------------------------
def create_stock_entry(doc):
    fuel_items = [
        item for item in doc.items
        if frappe.get_value("Item", item.item_code, "item_group") == "Fuel"
    ]

    if not fuel_items:
        return None

    company_abbr = frappe.get_value("Company", doc.company, "abbr")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Transfer"
    stock_entry.set_posting_time = 1
    stock_entry.posting_time = doc.time
    stock_entry.posting_date = doc.date
    stock_entry.custom_employee = doc.employee
    stock_entry.custom_cash_sales_app = doc.name

    for item in fuel_items:
        source_warehouse = item.warehouse

        source_warehouse_strip = (
            source_warehouse[:-len(f" - {company_abbr}")].strip()
            if f" - {company_abbr}" in source_warehouse else source_warehouse
        )

        warehouse = frappe.get_all(
            "Warehouse",
            filters={"warehouse_name": source_warehouse_strip},
            fields=["default_in_transit_warehouse"]
        )

        if warehouse:
            in_transit = warehouse[0].get("default_in_transit_warehouse")

            if not in_transit:
                frappe.throw(_("Transit warehouse not set in Warehouse"))

            stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "s_warehouse": in_transit,
                "t_warehouse": source_warehouse
            })

    stock_entry.insert()
    stock_entry.submit()

    return stock_entry.name


# -----------------------------
# STEP 2: SALES INVOICE
# -----------------------------
def create_sales_invoice(doc):
    if doc.sales_invoice_created:
        return doc.sales_invoice_created

    si = frappe.new_doc("Sales Invoice")
    si.customer = doc.customer
    si.discount_amount = doc.additional_discount_amount
    si.due_date = doc.due_date
    si.allocate_advances_automatically = 0 if doc.include_payments else 1
    si.cost_center = doc.station
    si.update_stock = 1
    si.set_posting_time = 1
    si.selling_price_list = doc.price_list
    si.posting_date = doc.date
    si.posting_time = doc.time
    si.additional_discount_account = "5125 - Discounts on Fuel - SE"
    si.custom_invoice_no = doc.invoice_no
    si.custom_fuel_sales_app_id = doc.name
    si.custom_employee = doc.employee

    remarks = ""

    for item in doc.items:
        si.append("items", {
            "item_code": item.item_code,
            "qty": item.qty,
            "rate": item.rate,
            "warehouse": item.warehouse,
            "amount": item.amount,
            "cost_center": doc.station,
            "custom_vehicle_plates": item.number_plate
        })

        if item.number_plate:
            remarks += f"{item.item_code} | Qty: {item.qty} | Plate: {item.number_plate}\n"

    si.remarks = remarks

    si.insert()
    si.submit()

    doc.db_set("sales_invoice_created", si.name)
    doc.db_set("net_total", si.net_total)

    return si.name


# -----------------------------
# STEP 3: PAYMENTS
# -----------------------------
def create_payments(doc, sales_invoice_name):
    if not doc.include_payments:
        return

    outstanding_amount = frappe.get_value(
        "Sales Invoice",
        sales_invoice_name,
        "outstanding_amount"
    )

    pos_profile = doc.items[0].pos_profile if doc.items else None

    payment_methods = frappe.get_all(
        "POS Payment Method",
        filters={"parent": pos_profile},
        fields=["mode_of_payment"]
    )

    for pm in payment_methods:
        mode = pm.mode_of_payment
        mop_doc = frappe.get_doc("Mode of Payment", mode)

        default_account = mop_doc.accounts[0].default_account
        currency = frappe.db.get_value("Account", default_account, "account_currency")

        pe = frappe.new_doc("Payment Entry")
        pe.party_type = "Customer"
        pe.payment_type = "Receive"
        pe.posting_date = doc.date
        pe.party = doc.customer
        pe.paid_amount = outstanding_amount
        pe.received_amount = outstanding_amount
        pe.target_exchange_rate = 1.0
        pe.paid_to = default_account
        pe.paid_to_account_currency = currency
        pe.mode_of_payment = mode
        pe.custom_fuel_sales_app_id = doc.name
        pe.custom_employee = doc.employee
        pe.cost_center = doc.station

        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": sales_invoice_name,
            "allocated_amount": outstanding_amount
        })

        pe.insert()
        pe.submit()


# -----------------------------
# WHITELIST METHODS (FOR JS)
# -----------------------------
@frappe.whitelist()
def process_stock(docname):
    doc = frappe.get_doc("Fuel Sales App", docname)
    result = create_stock_entry(doc)
    return result or "No Fuel Items"


@frappe.whitelist()
def process_invoice(docname):
    doc = frappe.get_doc("Fuel Sales App", docname)
    return create_sales_invoice(doc)


@frappe.whitelist()
def process_payment(docname):
    doc = frappe.get_doc("Fuel Sales App", docname)

    if not doc.sales_invoice_created:
        frappe.throw("Create Sales Invoice first")

    create_payments(doc, doc.sales_invoice_created)
    return "Payments Created"