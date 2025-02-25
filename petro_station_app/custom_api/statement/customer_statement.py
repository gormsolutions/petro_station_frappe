import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_customers(customer=None, from_date=None, to_date=None):
    if not customer or not from_date or not to_date:
        frappe.throw("Customer, From Date, and To Date are required.")

    sales_invoice_data = []
    total_paid_amount = 0
    grand_total_amount = 0  # Variable to hold the grand total of all amounts
    running_balance = 0      # Variable to hold the running balance
    balance_brought_forward = 0  # Variable to hold the balance brought forward

    try:
        # Step 1: Calculate Balance Brought Forward (balance before the 'from_date')
        previous_balance = frappe.db.sql("""
            SELECT 
                SUM(gle.debit - gle.credit) AS balance
            FROM 
                `tabGL Entry` gle
            WHERE 
                gle.party_type = 'Customer'
                AND gle.party = %s
                AND gle.posting_date < %s
                AND gle.docstatus = 1
        """, (customer, from_date), as_dict=True)

        if previous_balance and previous_balance[0].balance:
            balance_brought_forward = flt(previous_balance[0].balance)

        # Initialize running balance with balance brought forward
        running_balance = balance_brought_forward

        # Step 2: Fetch Sales Invoices and their items for the specified customer and date range
        customer_statement = frappe.db.sql("""
            SELECT 
                si.name AS invoice_name,
                si.cash_refund_id AS cash_refund_id,
                si.credit_sales_id AS credit_sales_id,
                si.posting_date,
                si.invoice_no,
                si.station, 
                sii.item_code, 
                sii.number_plate,
                sii.order_number,  
                sii.qty, 
                sii.rate, 
                sii.amount
            FROM 
                `tabCustomer Document` si
            JOIN 
                `tabFuel Sales Items` sii ON sii.parent = si.name
            WHERE 
                si.customer = %s 
                AND si.posting_date BETWEEN %s AND %s 
                AND si.docstatus = 1
        """, (customer, from_date, to_date), as_dict=True)

        for invoice in customer_statement:
            total_amount = flt(invoice.amount)
            grand_total_amount += total_amount  # Add to grand total
            running_balance += total_amount  # Update running balance
            
            invoice_data = {
                "invoice_name": invoice.invoice_name,
                "cost_center": invoice.station,
                "cash_refund_id": invoice.cash_refund_id,
                "credit_sales_id": invoice.credit_sales_id,
                "posting_date": invoice.posting_date,
                "item_code": invoice.item_code,
                "custom_vehicle_plates": invoice.number_plate,
                "invoice_no": invoice.invoice_no,
                "order_number": invoice.order_number,
                "qty": flt(invoice.qty),
                "rate": flt(invoice.rate),
                "amount": total_amount,
                "running_balance": running_balance  # Include running balance for each invoice
            }
            sales_invoice_data.append(invoice_data)

        # Step 3: Fetch Payment Entries within the specified date range for the same customer
        payments = frappe.db.sql("""
            SELECT 
                pe.name AS payment_entry_name, 
                pe.posting_date,
                pe.cost_center, 
                pe.paid_amount
            FROM 
                `tabPayment Entry` pe
            WHERE 
                pe.party_type = 'Customer'
                AND pe.party = %s
                AND pe.posting_date BETWEEN %s AND %s
                AND pe.docstatus = 1
        """, (customer, from_date, to_date), as_dict=True)

        filtered_payments = []
        for payment in payments:
            total_paid_amount += flt(payment.paid_amount)
            running_balance -= flt(payment.paid_amount)  # Subtract payment from running balance
            filtered_payments.append({
                "payment_entry_name": payment.payment_entry_name,
                "cost_center": payment.cost_center,
                "posting_date": payment.posting_date,
                "paid_amount": payment.paid_amount
            })

        # Step 4: Fetch GL Entries for the customer where voucher type is Journal Entry
        gl_entries = frappe.db.sql("""
            SELECT
                gle.name AS gl_entry_name,
                gle.posting_date,
                gle.cost_center,
                gle.debit,
                gle.voucher_no,
                gle.credit,
                gle.remarks
            FROM
                `tabGL Entry` gle
            WHERE
                gle.party_type = 'Customer'
                AND gle.party = %s
                AND gle.voucher_type = 'Sales Invoice'
                AND gle.is_opening = 'Yes'
                AND gle.posting_date BETWEEN %s AND %s
                AND gle.docstatus = 1
        """, (customer, from_date, to_date), as_dict=True)

        filtered_gl_entries = []
        for gl_entry in gl_entries:
            filtered_gl_entries.append({
                "gl_entry_name": gl_entry.gl_entry_name,
                "posting_date": gl_entry.posting_date,
                "cost_center": gl_entry.cost_center,
                "voucher_no": gl_entry.voucher_no,
                "debit": flt(gl_entry.debit),
                "credit": flt(gl_entry.credit),
                "remarks": gl_entry.remarks
            })

            # Update running balance: add debit amounts and subtract credit amounts
            running_balance += flt(gl_entry.debit)  # Add debit to running balance
            running_balance -= flt(gl_entry.credit)  # Subtract credit from running balance
            total_paid_amount += flt(gl_entry.credit)  # Add credit to total paid

        # Step 5: Calculate outstanding amount
        outstanding_amount = grand_total_amount - total_paid_amount

        # Return the complete result set
        return {
            "sales_invoice_data": sales_invoice_data,
            "balance_brought_forward": balance_brought_forward,
            "grand_total_amount": grand_total_amount,
            "total_paid_amount": total_paid_amount,
            "outstanding_amount": outstanding_amount,
            "payments": filtered_payments,
            "gl_entries": filtered_gl_entries,
            "running_balance": running_balance  # Include the final running balance in the response
        }

    except Exception as e:
        frappe.throw(f"An error occurred while fetching customer data: {str(e)}")
