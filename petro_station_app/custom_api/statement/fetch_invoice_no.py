# custom_app/api/customer.py

import frappe

@frappe.whitelist()
def update_customer_invoices():
    # Get all Customer documents with a non-empty `credit_sales_id`
    customers = frappe.get_all('Customer Document', filters={'credit_sales_id': ['!=', '']}, fields=['name', 'credit_sales_id'])
    updated_customers = []
    
    for customer in customers:
        # Fetch invoice_no from Credit Sales App based on credit_sales_id
        credit_sales_records = frappe.get_all('Credit Sales App', filters={'name': customer.credit_sales_id}, fields=['invoice_no'])
        
        if credit_sales_records:
            # Combine all invoice_no values into a single comma-separated string
            invoice_no_string = ', '.join([record['invoice_no'] for record in credit_sales_records])

            # Update the invoice_no field in Customer document
            frappe.db.set_value('Customer Document', customer['name'], 'invoice_no', invoice_no_string)
            updated_customers.append(customer['name'])
    
    # Commit changes to save updates to the database
    frappe.db.commit()
    
    return f"Updated invoice numbers for {len(updated_customers)} customers."
