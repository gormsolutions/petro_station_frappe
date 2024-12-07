import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_transaction_report_gl(transaction_id, station=None, from_date=None, to_date=None):
    # Fetch the Transaction Accounts document
    transaction_account_doc = frappe.get_doc("Transaction Accounts", transaction_id)
    account_names = [item.account for item in transaction_account_doc.trans_account_items]

    # Initialize conditions and parameters
    conditions = ["is_cancelled = 0"]  # Exclude canceled entries 
    params = {}

    # Add conditions based on optional filters
    if station:
        conditions.append("cost_center = %(cost_center)s")
        params["cost_center"] = station

    if from_date and to_date:
        conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    # Combine conditions into a single string
    condition_str = " AND ".join(conditions)

    # Query the GL Entry table
    debit_credit_data = frappe.db.sql(f"""
        SELECT 
            account, 
            SUM(debit) - SUM(credit) AS balance
        FROM 
            `tabGL Entry`
        WHERE 
            account IN %(account_names)s 
            {"AND " + condition_str if condition_str else ""}
        GROUP BY 
            account
    """, {
        "account_names": account_names,
        **params
    }, as_dict=True)

    return debit_credit_data



@frappe.whitelist()
def get_transaction_report_gl_withoutvivo(transaction_id, station=None, from_date=None, to_date=None):
    # Fetch the Transaction Accounts document
    transaction_account_doc = frappe.get_doc("Transaction Accounts", transaction_id)
    account_names = [item.account for item in transaction_account_doc.trans_account_items]

    # Initialize conditions and parameters
    conditions = ["is_cancelled = 0"]  # Exclude canceled entries
    params = {}

    # Add conditions based on optional filters
    if station:
        conditions.append("cost_center = %(cost_center)s")
        params["cost_center"] = station

    if from_date and to_date:
        conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    # Exclude the specific combination of account, party, and party_type
    conditions.append("NOT (account = '1310 - Debtors - SE' AND party = 'VIVO' AND party_type = 'Customer')")

    # Combine conditions into a single string
    condition_str = " AND ".join(conditions)

    # Query the GL Entry table
    debit_credit_data = frappe.db.sql(f"""
        SELECT 
            account, 
            SUM(debit) - SUM(credit) AS balance
        FROM 
            `tabGL Entry`
        WHERE 
            account IN %(account_names)s 
            {"AND " + condition_str if condition_str else ""}
        GROUP BY 
            account
    """, {
        "account_names": account_names,
        **params
    }, as_dict=True)

    return debit_credit_data

@frappe.whitelist()
def get_transaction_report_gl_withvivo(transaction_id, station=None, from_date=None, to_date=None):
    # Fetch the Transaction Accounts document
    transaction_account_doc = frappe.get_doc("Transaction Accounts", transaction_id)
    account_names = [item.account for item in transaction_account_doc.trans_account_items]

    # Initialize conditions and parameters
    conditions = ["is_cancelled = 0"]  # Exclude canceled entries
    params = {}

    # Add conditions based on optional filters
    if station:
        conditions.append("cost_center = %(cost_center)s")
        params["cost_center"] = station

    if from_date and to_date:
        conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    # Exclude the specific combination of account, party, and party_type
    conditions.append("account = '1310 - Debtors - SE' AND party = 'VIVO' AND party_type = 'Customer'")

    # Combine conditions into a single string
    condition_str = " AND ".join(conditions)

    # Query the GL Entry table
    debit_credit_data = frappe.db.sql(f"""
        SELECT 
            account, 
            SUM(debit) - SUM(credit) AS balance
        FROM 
            `tabGL Entry`
        WHERE 
            account IN %(account_names)s 
            {"AND " + condition_str if condition_str else ""}
        GROUP BY 
            account
    """, {
        "account_names": account_names,
        **params
    }, as_dict=True)

    return debit_credit_data


import frappe
from frappe.utils import flt, today

@frappe.whitelist()
def get_daily_totals(from_date=None, to_date=None, cost_center=None):
    """
    Fetch total sales and total expenses for a date range and cost center.
    If no date range is provided, it defaults to today's date.
    """
    if not from_date:
        from_date = today()
    if not to_date:
        to_date = today()

    # Initialize totals
    total_sales = 0.0
    total_expenses = 0.0

    # Define cost center condition dynamically
    cost_center_condition = "AND cost_center = %(cost_center)s" if cost_center else ""

    # Fetch total sales from Sales Invoices
    sales_data = frappe.db.sql(f"""
        SELECT 
            SUM(grand_total) AS total_sales
        FROM 
            `tabSales Invoice`
        WHERE 
            posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {cost_center_condition}
    """, {"from_date": from_date, "to_date": to_date, "cost_center": cost_center} if cost_center else {"from_date": from_date, "to_date": to_date}, as_dict=True)

    if sales_data and sales_data[0].get('total_sales'):
        total_sales = flt(sales_data[0].get('total_sales'))

    # Fetch GL Entries for the specified cost center and date range
    total_expenses_fromgl = frappe.get_all(
        "GL Entry",
        filters={
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 1,
        },
        fields=["name", "debit", "credit", "account", "posting_date", "cost_center"]
    )

    # Dictionary to store total debits and credits for each account
    total_expenses = 0.0
    for entry in total_expenses_fromgl:
        # Check if the account is an Expense Account and filter by the cost center if provided
        account_doc = frappe.get_doc("Account", entry['account'])
        if account_doc.account_type == "Expense Account":
            if cost_center and entry.get('cost_center') == cost_center or not cost_center:
                total_expenses += flt(entry.get('debit', 0)) - flt(entry.get('credit', 0))

    return {
        "from_date": from_date,
        "to_date": to_date,
        "cost_center": cost_center,
        "total_sales": total_sales,
        "total_expenses": total_expenses
    }
