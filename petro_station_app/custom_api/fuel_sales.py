import frappe
import json
from frappe import _

# ==============================
# MANAGER STEP 1: STOCK ENTRY
# ==============================
@frappe.whitelist()
def manager_create_stock_entry(doc):
	"""Create Stock Entry from Fuel Sales App document"""
	
	# Parse doc if it's a string (JSON)
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	# Convert dict to Frappe Document object
	if isinstance(doc, dict):
		doc = frappe.get_doc(doc)
	
	if "Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("Only Managers allowed"))

	if not doc.items:
		return "No items found"
	
	# Step 1: Filter fuel items from the item list
	fuel_items = [item for item in doc.items if frappe.get_value("Item", item.item_code, "item_group") == "Fuel"]

	# Step 2: Create Stock Entry for fuel items (if any)
	if not fuel_items:
		return "No fuel items found"
	
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

	if not stock_entry.items:
		frappe.throw(_("No valid stock entry items found"))

	stock_entry.insert()
	stock_entry.submit()

	frappe.db.set_value("Fuel Sales App", doc.name, "custom_stock_entry", stock_entry.name)

	return stock_entry.name


# ==============================
# MANAGER STEP 2: SALES INVOICE
# ==============================
@frappe.whitelist()
def manager_create_sales_invoice(doc):
	"""Create Sales Invoice from Fuel Sales App document"""
	
	# Parse doc if it's a string (JSON)
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	# Convert dict to Frappe Document object
	if isinstance(doc, dict):
		doc = frappe.get_doc(doc)
	
	if "Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("Only Managers allowed"))

	if doc.sales_invoice_created:
		return "Already created"

	if not doc.items:
		frappe.throw(_("No items found"))

	si = frappe.new_doc("Sales Invoice")
	si.customer = doc.customer
	si.discount_amount = doc.additional_discount_amount or 0
	si.due_date = doc.due_date
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

	remarks = []

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
			remarks.append(
				f"{item.item_code} | {item.qty} | {item.amount} | {item.number_plate}"
			)

	si.remarks = "\n".join(remarks) if remarks else None

	si.insert()
	si.submit()

	frappe.db.set_value("Fuel Sales App", doc.name, "sales_invoice_created", si.name)

	return si.name


# ==============================
# MANAGER STEP 3: PAYMENT (Simplified)
# ==============================
@frappe.whitelist()
def manager_create_payment(doc):
	"""Create Payment Entry from Fuel Sales App document"""
	
	# Parse doc if it's a string (JSON)
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	# Convert dict to Frappe Document object
	if isinstance(doc, dict):
		doc = frappe.get_doc(doc)
	
	if "Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("Only Managers allowed"))

	if not doc.sales_invoice_created:
		frappe.throw(_("Create Sales Invoice first"))

	# Get the sales invoice
	si = frappe.get_doc("Sales Invoice", doc.sales_invoice_created)

	if si.outstanding_amount <= 0:
		return "No outstanding amount"

	# Get default cash/bank account
	default_receivable_account = frappe.get_cached_value("Company", doc.company, "default_receivable_account")
	default_cash_account = frappe.get_cached_value("Company", doc.company, "default_cash_account")
	
	# Create payment entry
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = doc.customer
	pe.posting_date = doc.date
	pe.paid_amount = si.outstanding_amount
	pe.received_amount = si.outstanding_amount
	pe.target_exchange_rate = 1.0
	pe.paid_to = default_cash_account  # Or appropriate account
	pe.paid_to_account_currency = frappe.db.get_value("Account", default_cash_account, "account_currency")
	pe.custom_fuel_sales_app_id = doc.name
	pe.custom_employee = doc.employee
	pe.cost_center = doc.station

	pe.append("references", {
		"reference_doctype": "Sales Invoice",
		"reference_name": si.name,
		"allocated_amount": si.outstanding_amount
	})

	pe.insert()
	pe.submit()

	frappe.db.set_value("Fuel Sales App", doc.name, "custom_payment_entry", pe.name)

	return pe.name