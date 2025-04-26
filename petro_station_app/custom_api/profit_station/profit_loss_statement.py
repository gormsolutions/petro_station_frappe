import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils import getdate

# @frappe.whitelist()
# def get_grouped_profit_and_loss_with_details(from_date, to_date, cost_center=None):
#     filters = {
#         "posting_date": ["between", [from_date, to_date]],
#         "voucher_subtype": ["!=", "Internal Transfer"],  # Exclude 'Internal Transfer'
#     }
#     if cost_center:
#         filters["cost_center"] = cost_center

#     gl_entries = frappe.get_all(
#         "GL Entry",
#         filters=filters,
#         fields=[
#             "name as voucher_number",
#             "voucher_no",
#             "posting_date",
#             "account",
#             "debit",
#             "credit",
#             "against_voucher",
#             "against_voucher_type",
#             "party_type",
#             "party",
#             "voucher_subtype",  # Add this field for clarity (if needed for debugging)
#         ],
#         order_by="posting_date asc"
#     )

#     grouped_data = {
#         "COGS": {"total": 0.0, "entries": []},
#         "Expenses": {"total": 0.0, "entries": []},
#         "Invoices": {"total": 0.0, "entries": []},
#         "Other": {"total": 0.0, "entries": []}  # Added 'Other' category
#     }

#     for entry in gl_entries:
#         account_doc = frappe.get_doc("Account", entry["account"]) if entry["account"] else None
#         account_type = account_doc.account_type if account_doc else "N/A"
#         root_type = account_doc.root_type if account_doc else "N/A"

#         # Only process if root_type is either 'Income' or 'Expense'
#         if root_type not in ["Income", "Expense"]:
#             continue

#         debit_amount = flt(entry.get("debit", 0))  # Ensure debit is a float
#         credit_amount = flt(entry.get("credit", 0))  # Ensure credit is a float
#         amount = debit_amount - credit_amount

#         # Categorize and group entries based on account type
#         if "Cost of Goods Sold" in account_type:  # COGS-related entries
#             grouped_data["COGS"]["total"] += amount
#             grouped_data["COGS"]["entries"].append(entry)
#         elif "Expense Account" in account_type:  # Expense-related entries
#             grouped_data["Expenses"]["total"] += amount
#             grouped_data["Expenses"]["entries"].append(entry)
#         elif any(x in account_type for x in ["Income Account", "Bank", "Cash"]):  # Invoice-related entries (includes Bank and Cash)
#             grouped_data["Invoices"]["total"] += amount
#             grouped_data["Invoices"]["entries"].append(entry)
#         else:
#             # Merge unclassified entries into 'Other' category
#             grouped_data["Other"]["total"] += amount
#             grouped_data["Other"]["entries"].append(entry)

#     # Calculate Total Income (Credits from Invoices + Other income)
#     total_income = sum(flt(entry.get("credit", 0)) for entry in grouped_data["Invoices"]["entries"])
#     total_income += sum(flt(entry.get("credit", 0)) for entry in grouped_data["Other"]["entries"])


#     total_credit_invo = sum(flt(entry.get("credit", 0)) for entry in grouped_data["Invoices"]["entries"])
#     total_credit_other = sum(flt(entry.get("credit", 0)) for entry in grouped_data["Other"]["entries"])

#     # Calculate Total Expense (Debits from COGS + Expenses + Other)
#     total_expense = sum(flt(entry.get("debit", 0)) for entry in grouped_data["COGS"]["entries"] + grouped_data["Expenses"]["entries"])

#     # Net Profit = Total Income - Total Expense
#     net_profit = total_income - total_expense

#     total_debit = sum([group["total"] for group in grouped_data.values()])
#     total_credit = total_debit  # Assuming debit and credit are balanced

#     return {
#         "grouped_data": grouped_data,
#         "total_income": total_income,
#         "total_expense": total_expense,
#         # "total_credit_invo": total_credit_invo,
#         # "total_credit_other": total_credit_other,
#         "net_profit": net_profit,
#         "total_debit": total_debit,
#         "total_credit": total_credit,
#     }


import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_grouped_profit_and_loss_with_details(from_date, to_date, cost_center=None):
    filters = {
        "posting_date": ["between", [from_date, to_date]],
        "voucher_subtype": ["!=", "Internal Transfer"],  # Exclude 'Internal Transfer'
        "is_cancelled": 0
    }
    if cost_center:
        filters["cost_center"] = cost_center

    gl_entries = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=[
            "name as voucher_number",
            "voucher_no",
            "posting_date",
            "account",
            "debit",
            "credit",
            "against_voucher",
            "against_voucher_type",
            "party_type",
            "party",
            "voucher_subtype",  # Add this field for clarity (if needed for debugging)
        ],
        order_by="posting_date asc"
    )

    grouped_data = {
        "COGS": {"total": 0.0, "entries": []},
        "Expenses": {"total": 0.0, "entries": []},  # Corrected key
        "Invoices": {"total": 0.0, "entries": []},
        "Other": {"total": 0.0, "entries": []}  # Added 'Other' category
    }

    for entry in gl_entries:
        account_doc = frappe.get_doc("Account", entry["account"]) if entry["account"] else None
        account_type = account_doc.account_type if account_doc else "N/A"
        root_type = account_doc.root_type if account_doc else "N/A"

        # Only process if root_type is either 'Income' or 'Expense'
        if root_type not in ["Income", "Expense"]:
            continue

        debit_amount = flt(entry.get("debit", 0))  # Ensure debit is a float
        credit_amount = flt(entry.get("credit", 0))  # Ensure credit is a float
        amount = debit_amount - credit_amount

        # Categorize and group entries based on account type
        if "Cost of Goods Sold" in account_type:  # COGS-related entries
            grouped_data["COGS"]["total"] += amount
            grouped_data["COGS"]["entries"].append(entry)
        elif root_type == "Expense" and account_type != "Cost of Goods Sold":  # Expense-related entries
            grouped_data["Expenses"]["total"] += amount  # Corrected key
            grouped_data["Expenses"]["entries"].append(entry)  # Corrected key
        elif any(x in account_type for x in ["Income Account", "Bank", "Cash"]):  # Invoice-related entries (includes Bank and Cash)
            grouped_data["Invoices"]["total"] += amount
            grouped_data["Invoices"]["entries"].append(entry)
        else:
            # Merge unclassified entries into 'Other' category
            grouped_data["Other"]["total"] += amount
            grouped_data["Other"]["entries"].append(entry)

    # Calculate Total Income (Credits from Invoices + Other income)
    total_income = sum(flt(entry.get("credit", 0)) for entry in grouped_data["Invoices"]["entries"])
    total_income += sum(flt(entry.get("credit", 0)) for entry in grouped_data["Other"]["entries"])

    # Calculate Total Expense (Debits from COGS + Expenses + Other)
    total_expense = sum(flt(entry.get("debit", 0)) for entry in grouped_data["COGS"]["entries"] + grouped_data["Expenses"]["entries"])

    # Net Profit = Total Income - Total Expense
    net_profit = total_income - total_expense

    total_debit = sum([group["total"] for group in grouped_data.values()])
    total_credit = total_debit  # Assuming debit and credit are balanced

    return {
        "grouped_data": grouped_data,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }
