import frappe

# @frappe.whitelist()
# def fetch_transactions(account_name, station=None, from_date=None, to_date=None):
#     try:
#         # Prepare filters
#         filters = {"account": account_name, "cost_center": station}

#         # If both from_date and to_date are provided, fetch transactions between the exact dates
#         if from_date and to_date:
#             filters["posting_date"] = ["between", [from_date, to_date]]

#         # If only from_date is provided, fetch transactions on that exact date
#         elif from_date:
#             filters["posting_date"] = from_date

#         # If only to_date is provided, fetch transactions on that exact date
#         elif to_date:
#             filters["posting_date"] = to_date

#         # Fetch transactions from GL Entry
#         transactions = frappe.get_all(
#             "GL Entry",
#             filters=filters,
#             fields=["posting_date", "account", "debit", "voucher_subtype", "credit", "voucher_type", "voucher_no", "remarks"]
#         )

#         if not transactions:
#             print(f"No transactions found for account: {account_name} with the specified date range.")
#             return []

#         # Print and return the fetched transactions
#         for transaction in transactions:
#             print(transaction)

#         return transactions

#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return []


@frappe.whitelist()
def fetch_transactions(account_name, station=None, from_date=None, to_date=None):
    try:
        # Prepare filters
        filters = {"account": account_name, "cost_center": station}

        # If both from_date and to_date are provided, fetch transactions between the exact dates
        if from_date and to_date:
            filters["posting_date"] = ["between", [from_date, to_date]] 

        # If only from_date is provided, fetch transactions on that exact date
        elif from_date:
            filters["posting_date"] = from_date

        # If only to_date is provided, fetch transactions on that exact date
        elif to_date:
            filters["posting_date"] = to_date

        # Fetch transactions from GL Entry
        transactions = frappe.get_all(
            "GL Entry",
            filters=filters,
            fields=["posting_date", "account", "debit", "voucher_subtype", "credit", "voucher_type", "voucher_no", "remarks"]
        )

        # Add employee full name to each transaction
        for transaction in transactions:
            if transaction.get("voucher_type") in ["Journal Entry", "Payment Entry", "Sales Invoice", "Stock Entry"]:
                # Fetch the custom_employee field
                custom_employee = frappe.db.get_value(
                    transaction["voucher_type"],
                    transaction["voucher_no"],
                    "custom_employee"
                )

                # Fetch the employee full name if the custom_employee exists
                if custom_employee:
                    transaction["employee_name"] = frappe.db.get_value("Employee", custom_employee, "employee_name")
                else:
                    transaction["employee_name"] = None
                    
                

        return transactions

    except Exception as e:
        frappe.log_error(message=f"Error in fetch_transactions: {e}", title="Fetch Transactions Error")
        return []


