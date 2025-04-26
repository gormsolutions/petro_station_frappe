import frappe
from frappe import _
@frappe.whitelist()
def get_fuel_sales_with_only_stock_entry(cost_center):
    # Get Fuel Sales App names from Stock Entry where cost center matches
    stock_entry_refs = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_cash_sales_app": ["!=", ""],
            "cost_center": cost_center,
             "docstatus": 1
        },
        fields=["custom_cash_sales_app"]
    )
    stock_app_names = [d.custom_cash_sales_app for d in stock_entry_refs]

    if not stock_app_names:
        return []

    # Get Fuel Sales App names from Sales Invoice where cost center matches
    sales_invoice_refs = frappe.get_all(
        "Sales Invoice",
        filters={
            "custom_fuel_sales_app_id": ["in", stock_app_names],
            "cost_center": cost_center,
             "docstatus": 1
        },
        fields=["custom_fuel_sales_app_id"]
    )
    sales_invoice_app_ids = {d.custom_fuel_sales_app_id for d in sales_invoice_refs}

    # Filter names that are in Stock Entry but not yet in Sales Invoice
    only_in_stock_entries = [name for name in stock_app_names if name not in sales_invoice_app_ids]

    # Fetch actual Fuel Sales App documents with matching cost center
    result = frappe.get_all(
        "Fuel Sales App",
        filters={
            "name": ["in", only_in_stock_entries],
            "station": cost_center,
            "docstatus": 1
        },
        fields=["name", "date", "station"]
    )

    return result


@frappe.whitelist()
def get_fuel_credit_with_only_stock_entry(cost_center):
    # Get Fuel Sales App names from Stock Entry where cost center matches
    stock_entry_refs = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_credit_sales_app": ["!=", ""],
            "cost_center": cost_center,
             "docstatus": 1
        },
        fields=["custom_credit_sales_app"]
    )
    stock_app_names = [d.custom_credit_sales_app for d in stock_entry_refs]

    if not stock_app_names:
        return []

    # Get Fuel Sales App names from Sales Invoice where cost center matches
    sales_invoice_refs = frappe.get_all(
        "Sales Invoice",
        filters={
            "custom_credit_sales_app": ["in", stock_app_names],
            "cost_center": cost_center,
             "docstatus": 1
        },
        fields=["custom_credit_sales_app"]
    )
    sales_invoice_app_ids = {d.custom_credit_sales_app for d in sales_invoice_refs}

    # Filter names that are in Stock Entry but not yet in Sales Invoice
    only_in_stock_entries = [name for name in stock_app_names if name not in sales_invoice_app_ids]

    # Fetch actual Fuel Sales App documents with matching cost center
    result = frappe.get_all(
        "Credit Sales App",
        filters={
            "name": ["in", only_in_stock_entries],
            "station": cost_center,
            "docstatus": 1
        },
        fields=["name", "date", "station"]
    )

    return result
