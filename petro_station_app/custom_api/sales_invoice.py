import frappe
from frappe.utils import nowdate, flt

def create_wht_journal_entry(doc, method):
    customer = frappe.get_doc("Customer", doc.customer)

    if not customer.get("custom_has_wht"):
        return  # Skip if customer is not flagged for WHT

    wht_rate = 0.06  # 6% WHT
    wht_amount = 0.0

    # Calculate WHT on all items (or you can filter with `is_taxable` if needed)
    for item in doc.items:
        wht_amount += flt(item.net_amount) * wht_rate

    wht_amount = round(wht_amount, 2)

    if not wht_amount:
        return  # No WHT amount calculated

    # Create Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = doc.company
    je.posting_date = doc.posting_date or nowdate()
    je.custom_wht_si_id = doc.name  # Link to Sales Invoice via custom field
    je.remark = f"WHT 6% for Sales Invoice {doc.name}"

    # Debit: WHT - SE (withholding tax account)
    je.append("accounts", {
        "account": "WHT - SE",  # Replace with your actual WHT asset/advance account
        "debit_in_account_currency": wht_amount,
        "cost_center": doc.cost_center,
    })

    # Credit: Customer receivable, linked to this Sales Invoice
    je.append("accounts", {
        "account": "1310 - Debtors - SE",  # Replace with your actual receivable account
        "party_type": "Customer",
        "party": doc.customer,
        "credit_in_account_currency": wht_amount,
        "cost_center": doc.cost_center,
        "reference_type": "Sales Invoice",
        "reference_name": doc.name,
    })

    je.insert(ignore_permissions=True)
    je.submit()

    # Link the Journal Entry back to the Sales Invoice
    doc.db_set("custom_wht_journal_id", je.name)  # Ensure this custom field exists on Sales Invoice
