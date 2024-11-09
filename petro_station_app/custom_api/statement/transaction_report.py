import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_transaction_report_gl(transaction_id, station=None, from_date=None, to_date=None):
    transaction_account_doc = frappe.get_doc("Transaction Accounts", transaction_id)
    account_names = [item.account for item in transaction_account_doc.trans_account_items]

    conditions = []
    params = {}

    if station:
        conditions.append("cost_center = %(cost_center)s")
        params["cost_center"] = station

    if from_date and to_date:
        conditions.append("posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params["from_date"] = from_date
        params["to_date"] = to_date

    condition_str = " AND ".join(conditions)

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

