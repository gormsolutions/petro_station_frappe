import frappe
from frappe.utils import flt
from frappe import _

@frappe.whitelist()
def fetch_sales_invoice_items(doc):
    """
    Compare rates of fuel items in Station Shift Management with Sales Invoice items.
    Fetch items if the rates differ and conditions (employee, date, station) match.
    """
    # Check if the doc is passed as a string (e.g., doc name)
    if isinstance(doc, str):
        doc = frappe.get_doc("Station Shift Management", doc)  # Assuming 'Station Shift Management' is the doctype

    # Ensure the document has the required data
    if not doc.get("overal_shift_closing_items"):
        return []

    fetched_items = []  # This will store the fetched items with differing rates

    # Fetch Sales Invoices matching employee, date, and station
    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "custom_employee": doc.employee,
            "posting_date": doc.from_date,
            "cost_center": doc.station
        },
        fields=["name"]
    )

    for sales_invoice in sales_invoices:
        # Load Sales Invoice
        invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice.name)

        for closing_item in doc.overal_shift_closing_items:
            # Only process fuel items
            if not closing_item.fuel:
                continue

            # Check if the fuel item exists in the Sales Invoice
            for invoice_item in invoice_doc.items:
                if invoice_item.item_code == closing_item.fuel:
                    # Compare rates
                    if flt(invoice_item.rate) != flt(closing_item.rate):
                        # If rates differ, add item details to the fetched_items list
                        fetched_items.append({
                            "item_code": invoice_item.item_code,
                            "qty": invoice_item.qty,
                            "rate": invoice_item.rate
                        })
                    break

    return sales_invoices  # Return the list of fetched items


@frappe.whitelist()
def get_grouped_sales_invoices_with_outstanding(cost_center=None, employee=None, posting_date=None, docname=None):
    try:
        # Log filter criteria
        frappe.logger().info(f"Fetching sales invoices for cost center: {cost_center}, employee: {employee}, and posting date: {posting_date}")

        # Build filters "outstanding_amount": [">", 0]
        filters = {"docstatus": 1}
        if cost_center:
            filters["cost_center"] = cost_center
        if posting_date:
            filters["posting_date"] = posting_date
        if employee:
            filters["custom_employee"] = employee

        # Fetch sales invoices
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters=filters,
            fields=["name", "posting_date", "custom_invoice_no", "customer_name", "customer", 
                    "grand_total", "outstanding_amount", "cost_center"]
        )
        frappe.logger().info(f"Fetched {len(sales_invoices)} sales invoices.")

        # Prepare aggregated items dictionary
        aggregated_items = {}

        # Fetch Station Shift Management document
        doc = frappe.get_doc("Station Shift Management", docname) if docname else None

        if doc and not doc.get("overal_shift_closing_items"):
            frappe.logger().info("No closing items found.")
            return {"Items": []}

        # Process invoices
        for invoice in sales_invoices:
            # Fetch items for the invoice
            items = frappe.get_all(
                "Sales Invoice Item",
                filters={"parent": invoice["name"]},
                fields=["item_code", "item_name", "qty", "rate", "amount", "discount_amount", "cost_center"]
            )

            # Check and aggregate items with mismatched rates
            for item in items:
                matching_item = next((ci for ci in doc.overal_shift_closing_items if ci.fuel == item["item_code"]), None)
                if matching_item and flt(item["rate"]) != flt(matching_item.rate):
                    key = (item["item_code"], item["rate"], item["cost_center"])  # Key for grouping

                    if key not in aggregated_items:
                        aggregated_items[key] = {
                            "Item Code": item["item_code"],
                            "Item Name": item["item_name"],
                            "Quantity": item["qty"],
                            "Rate": item["rate"],
                            "Amount": item["amount"],
                            "Discount Amount": item.get("discount_amount", 0),  # Handle missing key gracefully
                            "Cost Center": item["cost_center"]
                        }
                    else:
                        # Aggregate quantities and amounts
                        aggregated_items[key]["Quantity"] += item["qty"]
                        aggregated_items[key]["Amount"] += item["amount"]

        # Prepare final result
        result = {"Items": list(aggregated_items.values())}
        frappe.logger().info(f"Final grouped result: {result}")
        return result

    except Exception as e:
        frappe.logger().error(f"Error fetching and grouping sales invoices: {str(e)}")
        frappe.throw(_("An error occurred while grouping sales invoices: {}").format(str(e)))
