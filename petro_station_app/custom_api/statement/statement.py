import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_sales_invoice_details_and_payments(customer, from_date, to_date):
    sales_invoice_data = []
    refund_invoice_data = []
    total_paid_amount = 0
    grand_total_amount = 0  # Variable to hold the grand total of all amounts
    grand_total_amount_refund = 0
    running_balance = 0      # Variable to hold the running balance
    balance_brought_forward = 0  # Variable to hold the balance brought forward

    # Calculate Balance Brought Forward (balance before the 'from_date')
    previous_balance = frappe.db.sql("""
    SELECT 
        SUM(gle.debit - gle.credit) AS balance
    FROM 
        `tabGL Entry` gle
    WHERE 
        gle.party_type = 'Customer'
        AND gle.party = %s
        AND gle.posting_date < %s
        AND gle.is_cancelled = 0
        AND NOT EXISTS (
            SELECT 1 FROM `tabJournal Entry` je
            WHERE je.name = gle.voucher_no
            AND je.custom_cash_refund_id IS NOT NULL
            AND je.custom_cash_refund_id != ''
        )
    """, (customer, from_date), as_dict=True)

    
    if previous_balance and previous_balance[0].balance:
        balance_brought_forward = flt(previous_balance[0].balance)
    
    # Initialize running balance with balance brought forward
    running_balance = balance_brought_forward

    # Step 1: Fetch Sales Invoices and their items for the specified customer and date range
    invoices = frappe.db.sql("""
        SELECT 
            si.name AS invoice_name,
            si.custom_fuel_sales_app_id AS sales_app_id,
            si.custom_credit_sales_app AS credit_sales_id,
            si.posting_date,
            si.custom_invoice_no,
            si.cost_center, 
            sii.item_code, 
            sii.custom_vehicle_plates, 
            sii.qty, 
            sii.rate, 
            sii.amount
        FROM 
            `tabSales Invoice` si
        JOIN 
            `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE 
            si.customer = %s 
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
    """, (customer, from_date, to_date), as_dict=True)

    for invoice in invoices:
        total_amount = flt(invoice.amount)
        grand_total_amount += total_amount  # Add to grand total
        running_balance += total_amount  # Update running balance 
        
        invoice_data = {
            "invoice_name": invoice.invoice_name,
            "invoice_no": invoice.custom_invoice_no,
            "cost_center":invoice.cost_center,
            "sales_app_id": invoice.sales_app_id,
            "credit_sales_id": invoice.credit_sales_id,
            "posting_date": invoice.posting_date,  # Add posting date to the invoice data
            "item_code": invoice.item_code,
            "custom_vehicle_plates": invoice.custom_vehicle_plates,
            "qty": flt(invoice.qty),
            "rate": flt(invoice.rate),
            "amount": total_amount,
            "running_balance": running_balance  # Include running balance for each invoice
        }
        
        sales_invoice_data.append(invoice_data)
        

    # Step 2: Fetch Payment Entries within the specified date range for the same customer
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
            "posting_date": payment.posting_date,  # Include posting date for payments
            "paid_amount": payment.paid_amount
        })

    # Step 3: Fetch GL Entries for the customer where voucher type is Journal Entry and custom_cash_refund_id is not set
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
        AND gle.voucher_type = 'Journal Entry'
        AND gle.posting_date BETWEEN %s AND %s
        AND gle.is_cancelled = 0
        AND NOT EXISTS (
            SELECT 1 FROM `tabJournal Entry` je
            WHERE je.name = gle.voucher_no
            AND je.custom_cash_refund_id IS NOT NULL
            AND je.custom_cash_refund_id != ''
        )
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

    # Calculate outstanding amount
    outstanding_amount = grand_total_amount - total_paid_amount
    
    # Step 4: Fetch Cash Refund Entries for the customer for the specified customer and date range
    
    
    cash_refund = frappe.db.sql("""
        SELECT 
            cr.name AS invoice_name,
            cr.date,
            cr.invoice_no,
            cr.station, 
            sii.item_code, 
            sii.number_plate, 
            sii.qty, 
            sii.rate, 
            sii.amount
        FROM 
            `tabCash Refund` cr
        JOIN 
            `tabFuel Sales Items` sii ON sii.parent = cr.name
        WHERE 
            cr.customer = %s 
            AND cr.date BETWEEN %s AND %s 
            AND cr.docstatus = 1
    """, (customer, from_date, to_date), as_dict=True)

    for cash_invoice in cash_refund:
        total_amount = flt(cash_invoice.amount)
        grand_total_amount_refund += total_amount  # Add to grand total
        running_balance += total_amount  # Update running balance 
        
        cash_refund_data = {
            "invoice_name": cash_invoice.invoice_name,
            "invoice_no": cash_invoice.invoice_no,
            "cost_center":cash_invoice.station,
            "posting_date": cash_invoice.date,  # Add posting date to the invoice data
            "item_code": cash_invoice.item_code,
            "custom_vehicle_plates": cash_invoice.number_plate,
            "qty": flt(cash_invoice.qty),
            "rate": flt(cash_invoice.rate),
            # "amount": flt(cash_invoice.amount),
            "amount": total_amount,
            "running_balance": running_balance  # Include running balance for each invoice
        }
        
        refund_invoice_data.append(cash_refund_data)
    
    
    
    
    return {
        "sales_invoice_data": sales_invoice_data,
        "refund_invoice_data": refund_invoice_data,
        "balance_brought_forward": balance_brought_forward,  # Include the balance brought forward
        "grand_total_amount": grand_total_amount,  # Return grand total of all amounts
        "total_paid_amount": total_paid_amount,
        "outstanding_amount": outstanding_amount,  # Return outstanding amount
        "payments": filtered_payments,  # Include filtered payment details in the result
        "gl_entries": filtered_gl_entries  # Include filtered GL entries in the result
    }
