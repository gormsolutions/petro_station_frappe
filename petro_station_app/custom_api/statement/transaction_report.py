import frappe # type: ignore
from frappe.utils import flt # type: ignore

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


import frappe # type: ignore
from frappe.utils import flt, today # type: ignore


# @frappe.whitelist()
# def get_daily_totals(from_date=None, to_date=None, cost_center=None):
#     """
#     Fetch total sales, total expenses, and detailed records for a date range and cost center.
#     If no date range is provided, it defaults to today's date.
#     """
#     if not from_date:
#         from_date = today()
#     if not to_date:
#         to_date = today() 

#     # Initialize totals and details
#     total_sales = 0.0
#     total_expenses = 0.0
#     sales_details = []
#     expense_details = []

#     # Define cost center condition dynamically
#     cost_center_condition = "AND cost_center = %(cost_center)s" if cost_center else ""

#     # Fetch sales invoice details
#     sales_data = frappe.db.sql(f"""
#         SELECT 
#             name, grand_total, customer, posting_date, cost_center
#         FROM 
#             `tabSales Invoice`
#         WHERE 
#             posting_date BETWEEN %(from_date)s AND %(to_date)s
#             AND docstatus = 1
#             {cost_center_condition}
#     """, {"from_date": from_date, "to_date": to_date, "cost_center": cost_center} if cost_center else {"from_date": from_date, "to_date": to_date}, as_dict=True)

#     for sale in sales_data:
#         total_sales += flt(sale.get('grand_total'))
#         sales_details.append(sale)

#     # Fetch GL Entry details
#     gl_entries = frappe.get_all(
#         "GL Entry",
#         filters={
#             "posting_date": ["between", [from_date, to_date]],
#             "docstatus": 1,
#         },
#         fields=["name", "debit", "credit", "account", "posting_date", "cost_center", "voucher_no"]
#     )

#     for entry in gl_entries:
#         # Check if the account is an Expense Account
#         account_doc = frappe.get_doc("Account", entry['account'])
#         if account_doc.account_type == "Expense Account":
#             if cost_center and entry.get('cost_center') == cost_center or not cost_center:
#                 entry['amount'] = flt(entry.get('debit', 0)) - flt(entry.get('credit', 0))

#                 # Check if the GL Entry is linked to a Journal Entry
#                 if frappe.db.exists("Journal Entry", entry.get('voucher_no')):
#                     journal_entry = frappe.get_doc("Journal Entry", entry.get('voucher_no'))

#                     # Fetch related descriptions from `Expense Claim Items` in `Station Expenses` and `Fuel Sales App`
#                     station_expenses = frappe.db.sql(f"""
#                         SELECT 
#                             eci.description
#                         FROM 
#                             `tabExpense Claim Items` eci
#                         JOIN 
#                             `tabStation Expenses` se ON eci.parent = se.name
#                         WHERE 
#                             se.name = %(journal_name)s
#                     """, {"journal_name": journal_entry.custom_station_expense_id}, as_dict=True)

#                     fuel_sales_app = frappe.db.sql(f"""
#                         SELECT 
#                             eci.description
#                         FROM 
#                             `tabExpense Claim Items` eci
#                         JOIN 
#                             `tabFuel Sales App` fsa ON eci.parent = fsa.name
#                         WHERE 
#                             fsa.name = %(journal_name)s
#                     """, {"journal_name": journal_entry.custom_fuel_expense_id}, as_dict=True)

#                     # Add descriptions to the entry
#                     entry['descriptions'] = {
#                         "station_expenses": [d['description'] for d in station_expenses],
#                         "fuel_sales_app": [d['description'] for d in fuel_sales_app]
#                     }

#                 total_expenses += entry['amount']
#                 expense_details.append(entry)

#     return {
#         "from_date": from_date,
#         "to_date": to_date,
#         "cost_center": cost_center,
#         "total_sales": total_sales,
#         "total_expenses": total_expenses,
#         "sales_details": sales_details,
#         "expense_details": expense_details
#     }

@frappe.whitelist()
def get_expense_totals(from_date=None, to_date=None, cost_center=None):
    """
    Fetch total expenses and detailed records for a date range and cost center.
    If no date range is provided, it defaults to today's date.
    """
    if not from_date:
        from_date = today()
    if not to_date:
        to_date = today()

    # Initialize totals and details
    total_expenses = 0.0
    expense_details = []

    # Define cost center condition dynamically
    cost_center_condition = "AND cost_center = %(cost_center)s" if cost_center else ""

    # Fetch GL Entry details for Expense Accounts
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 1,
        },
        fields=["name", "debit", "credit", "account", "posting_date", "cost_center", "voucher_no"]
    )

    for entry in gl_entries:
        # Check if the account is an Expense Account
        account_doc = frappe.get_doc("Account", entry['account'])
        if account_doc.account_type == "Expense Account":
            if cost_center and entry.get('cost_center') == cost_center or not cost_center:
                entry['amount'] = flt(entry.get('debit', 0)) - flt(entry.get('credit', 0))

                # Check if the GL Entry is linked to a Journal Entry
                if frappe.db.exists("Journal Entry", entry.get('voucher_no')):
                    journal_entry = frappe.get_doc("Journal Entry", entry.get('voucher_no'))

                    # Fetch related descriptions from `Expense Claim Items` in `Station Expenses` and `Fuel Sales App`
                    station_expenses = frappe.db.sql(f"""
                        SELECT 
                            eci.description
                        FROM 
                            `tabExpense Claim Items` eci
                        JOIN 
                            `tabStation Expenses` se ON eci.parent = se.name
                        WHERE 
                            se.name = %(journal_name)s
                    """, {"journal_name": journal_entry.custom_station_expense_id}, as_dict=True)

                    fuel_sales_app = frappe.db.sql(f"""
                        SELECT 
                            eci.description
                        FROM 
                            `tabExpense Claim Items` eci
                        JOIN 
                            `tabFuel Sales App` fsa ON eci.parent = fsa.name
                        WHERE 
                            fsa.name = %(journal_name)s
                    """, {"journal_name": journal_entry.custom_fuel_expense_id}, as_dict=True)

                    # Add descriptions to the entry
                    entry['descriptions'] = {
                        "station_expenses": [d['description'] for d in station_expenses],
                        "fuel_sales_app": [d['description'] for d in fuel_sales_app]
                    }

                total_expenses += entry['amount']
                expense_details.append(entry)

    return {
        "from_date": from_date,
        "to_date": to_date,
        "cost_center": cost_center,
        "total_expenses": total_expenses,
        "expense_details": expense_details
    }


@frappe.whitelist()
def get_daily_totals(from_date=None, to_date=None, cost_center=None):
    """
    Fetch total sales, total expenses, and detailed records for a date range and cost center.
    Includes separate totals and details for specific accounts like '1193 - Lubs Elgon Cash - SE'.
    """
    if not from_date:
        from_date = today()
    if not to_date:
        to_date = today()

    # Initialize totals and details
    total_sales = 0.0
    total_expenses = 0.0
    sales_details = []
    expense_details = []

    # Specific totals for lubs cash accounts
    lubs_cash_total = 0.0
    lubs_cash_details = []

    # Define cost center condition dynamically
    cost_center_condition = "AND cost_center = %(cost_center)s" if cost_center else ""

    # Fetch sales invoice details
    sales_data = frappe.db.sql(f"""
        SELECT 
            name, grand_total, customer, posting_date, cost_center
        FROM 
            `tabSales Invoice`
        WHERE 
            posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            {cost_center_condition}
    """, {"from_date": from_date, "to_date": to_date, "cost_center": cost_center} if cost_center else {"from_date": from_date, "to_date": to_date}, as_dict=True)

    for sale in sales_data:
        total_sales += flt(sale.get('grand_total'))
        sales_details.append(sale)

    # Fetch GL Entry details excluding specific accounts
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={
            "posting_date": ["between", [from_date, to_date]],
            "is_cancelled": 0,  # Ensure cancelled entries are excluded
            "account": ["not in", [
                "1193 - Lubs Elgon Cash - SE", 
                "1196 - Lubs Annex Cash - SE", 
                "1192 - Lubricants Sal Cash - SE", 
                "1198 - Lubs Mbale SS Cash - SE"
            ]],
        },
        fields=["name", "debit", "credit", "account", "posting_date", "cost_center", "voucher_no"]
    )

    for entry in gl_entries:
        account_doc = frappe.get_doc("Account", entry['account'])
        if account_doc.account_type == "Expense Account":
            if not cost_center or entry.get('cost_center') == cost_center:
                entry['amount'] = flt(entry.get('debit', 0)) - flt(entry.get('credit', 0))
                total_expenses += entry['amount']
                expense_details.append(entry)

    # Define specific lubs cash accounts to iterate over
    lubs_cash_accounts = [
        "1193 - Lubs Elgon Cash - SE",
        "1196 - Lubs Annex Cash - SE",
        "1192 - Lubricants Sal Cash - SE",
        "1198 - Lubs Mbale SS Cash - SE",
    ]

    for account in lubs_cash_accounts:
        lubs_cash_entries = frappe.get_all(
            "GL Entry",
            filters={
                "posting_date": ["between", [from_date, to_date]],
                "is_cancelled": 0,  # Ensure cancelled entries are excluded
                "account": account,
                # "voucher_subtype": ["!=", "Internal Transfer"],
                **({"cost_center": cost_center} if cost_center else {}),
            },
            fields=["name", "debit", "credit", "account", "posting_date", "cost_center", "voucher_no"]
        )

        for entry in lubs_cash_entries:
            entry['amount'] = flt(entry.get('debit', 0)) - flt(entry.get('credit', 0))
            lubs_cash_total += entry['amount']
            lubs_cash_details.append(entry)

    return {
        "from_date": from_date,
        "to_date": to_date,
        "cost_center": cost_center,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "sales_details": sales_details,
        "expense_details": expense_details,
        "lubs_cash_total": lubs_cash_total,
        "lubs_cash_details": lubs_cash_details,
    }
