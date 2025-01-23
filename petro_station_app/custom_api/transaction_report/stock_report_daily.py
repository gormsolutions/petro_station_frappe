import frappe
from frappe import _

@frappe.whitelist()
def get_daily_sales_stock_balance(date):
    # Get the stock ledger entries for a specific date
    stock_entries = frappe.get_all(
        'Stock Ledger Entry',
        filters={
            'posting_date': ['>=', date],
            'posting_date': ['<=', date]
        },
        fields=['item_code', 'qty_after_transaction', 'posting_date', 'voucher_type', 'voucher_no'],
        order_by='posting_date'
    )

    stock_balance = {}

    # Iterate over each stock entry to calculate the opening and closing balance
    for entry in stock_entries:
        if entry.item_code not in stock_balance:
            stock_balance[entry.item_code] = {'opening': 0, 'closing': 0}

        # Calculate the opening balance for the first entry of the day
        if entry.posting_date == date:
            if entry.voucher_type == 'Stock Reconciliation':
                # If this is a stock reconciliation, update the balance
                stock_balance[entry.item_code]['opening'] = entry.qty_after_transaction
            else:
                stock_balance[entry.item_code]['closing'] = entry.qty_after_transaction

    return stock_balance
