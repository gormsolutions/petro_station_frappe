import frappe
from frappe import _
from frappe.utils import cint

@frappe.whitelist()
def get_unposted_sales_invoices():
    # Step 1: Get cost centers with parent 'Hashim Gas Limited - SE'
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={"parent_cost_center": "Hashim Gas Limited - SE"},
        pluck="name"
    )

    if not cost_centers:
        return {"message": "No cost centers found under Hashim Gas Limited - SE"}

    # Step 2: Get sales invoices not found in GL Entry
    # Collect sales invoices from GL Entry
    posted_invoices = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": "Sales Invoice"},
        pluck="voucher_no"
    )

    # Step 3: Get Sales Invoices where items.cost_center is in the list and not posted
    sales_invoices = frappe.db.sql("""
        SELECT DISTINCT si.name,si.posting_date,si.customer_name
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.cost_center IN %(cost_centers)s
        AND si.docstatus = 1
        {not_in_gl}
        ORDER BY si.posting_date DESC
    """.format(
        not_in_gl="AND si.name NOT IN %(posted_invoices)s" if posted_invoices else ""
    ), {
        "cost_centers": tuple(cost_centers),
        "posted_invoices": tuple(posted_invoices)
    }, as_dict=True)

    return sales_invoices
