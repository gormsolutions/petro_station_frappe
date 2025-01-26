import frappe

@frappe.whitelist()
def get_unmatched_fuel_sales_apps_with_valid_stock_entries():
    """
    Fetch Sales Invoices where custom_fuel_sales_app_id is not set (null or empty),
    excluding canceled and draft invoices, and return unmatched Fuel Sales App names
    along with such Sales Invoices.
    
    Returns:
        dict: A dictionary containing:
              - not_set_sales_invoices: A list of Sales Invoices with no custom_fuel_sales_app_id.
              - unmatched_fuel_sales_apps: A list of unmatched Fuel Sales App names.
    """
    try:
        # Step 1: Get all Fuel Sales App names
        all_fuel_sales_apps = frappe.get_all("Fuel Sales App", fields=["name"])
        fuel_sales_app_names = {app["name"] for app in all_fuel_sales_apps}

        # Step 2: Fetch Sales Invoices where custom_fuel_sales_app_id is not set, excluding canceled and drafts
        not_set_sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={
                "custom_fuel_sales_app_id": ["is", "not set"],  # Check for unset values
                "docstatus": 1  # Only include submitted invoices
            },
            fields=["name", "posting_date", "customer", "custom_fuel_sales_app_id"]
        )
        
        # Extract custom_fuel_sales_app_id values from not_set_sales_invoices
        not_set_sales_app_ids = {
            invoice["custom_fuel_sales_app_id"]
            for invoice in not_set_sales_invoices
            if invoice["custom_fuel_sales_app_id"]
        }

        # Step 3: Identify unmatched Fuel Sales Apps
        unmatched_fuel_sales_apps = list(fuel_sales_app_names - not_set_sales_app_ids)

        # Return results
        return {
            "not_set_sales_invoices": not_set_sales_invoices,
            "unmatched_fuel_sales_apps": unmatched_fuel_sales_apps,
        }

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Fuel Sales App Matching Error")
        return {"error": str(e)}
