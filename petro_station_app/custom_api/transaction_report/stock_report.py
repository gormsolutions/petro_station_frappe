import frappe

@frappe.whitelist()
def fetch_stock_entry_ledger_data(from_date=None, to_date=None, cost_center=None):
    try:
        # Define filters
        filters = {
            'is_cancelled': 0,  # Exclude cancelled entries
            'voucher_type': ['in', ['Purchase Invoice', 'Sales Invoice']]
        }

        # Add optional filters
        if from_date and to_date:
            filters['posting_date'] = ['between', [from_date, to_date]]

        # Fetch warehouses linked to the given cost center
        warehouses = []
        if cost_center:
            warehouses = frappe.get_all(
                'Warehouse',
                filters={'custom_cost_centre': cost_center},
                pluck='name'
            )
            if warehouses:
                filters['warehouse'] = ['in', warehouses]

        # Fetch data from Stock Ledger Entry based on the given filters
        stock_entries = frappe.get_all(
            'Stock Ledger Entry',
            filters=filters,
            fields=['voucher_no', 'voucher_type', 'actual_qty', 'valuation_rate', 'warehouse', 'item_code', 'posting_date']
        )

        result = {
            'Purchase Invoice': [],
            'Sales Invoice': []
        }

        # Dictionary to accumulate grouped items
        grouped_items = {}

        for entry in stock_entries:
            # Fetch custom cost center from the warehouse
            custom_cost_center = frappe.db.get_value('Warehouse', entry.warehouse, 'custom_cost_centre')

            data = {
                'voucher_no': entry.voucher_no,
                'voucher_type': entry.voucher_type,
                'qty_change': entry.actual_qty,
                'valuation_rate': entry.valuation_rate or 0,  # Default to 0 if None
                'warehouse': entry.warehouse,
                'item_code': entry.item_code,
                'posting_date': entry.posting_date,
                'custom_cost_center': custom_cost_center
            }

            # Grouping data by item_code to avoid duplicates
            if entry.item_code not in grouped_items:
                grouped_items[entry.item_code] = {
                    'qty_in': 0,
                    'qty_out': 0,
                    'buying_price': 0,
                    'selling_price': 0,
                    'total_buying_amount': 0,
                    'total_selling_amount': 0,
                    'buying_price_count': 0,
                    'selling_price_count': 0,
                    'item_code': entry.item_code
                }

            if entry.voucher_type == 'Purchase Invoice':
                # For Purchase Invoice, accumulate purchase quantities and buying prices
                grouped_items[entry.item_code]['qty_in'] += entry.actual_qty
                grouped_items[entry.item_code]['buying_price'] += entry.valuation_rate or 0  # Avoid None
                grouped_items[entry.item_code]['total_buying_amount'] += (entry.actual_qty * (entry.valuation_rate or 0))
                grouped_items[entry.item_code]['buying_price_count'] += 1
            elif entry.voucher_type == 'Sales Invoice':
                # For Sales Invoice, accumulate sales quantities and selling prices
                grouped_items[entry.item_code]['qty_out'] += entry.actual_qty
                # Fetch the rate from the Sales Invoice Item
                sales_invoice_rate = frappe.db.get_value(
                    'Sales Invoice Item',
                    {'parent': entry.voucher_no, 'item_code': entry.item_code},
                    'rate'
                ) or 0  # Default to 0 if rate is None
                grouped_items[entry.item_code]['selling_price'] += sales_invoice_rate
                grouped_items[entry.item_code]['total_selling_amount'] += (entry.actual_qty * sales_invoice_rate)
                grouped_items[entry.item_code]['selling_price_count'] += 1

        # Converting grouped items into the result format
        for item_code, values in grouped_items.items():
            # Calculate the average buying price (valuation_rate for Purchase Invoice)
            avg_buying_price = values['buying_price'] / values['buying_price_count'] if values['buying_price_count'] > 0 else 0
            # Calculate the average selling price (rate for Sales Invoice)
            avg_selling_price = values['selling_price'] / values['selling_price_count'] if values['selling_price_count'] > 0 else 0

            result['Purchase Invoice'].append({
                'item_code': item_code,
                'qty_in': values['qty_in'],
                'buying_price': avg_buying_price,  # Average buying price (valuation_rate)
                'total_buying_amount': values['total_buying_amount'],
            })
            result['Sales Invoice'].append({
                'item_code': item_code,
                'qty_out': values['qty_out'],
                'selling_price': avg_selling_price,  # Average selling price (rate)
                'total_selling_amount': values['total_selling_amount'],
            })

        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Fetch Stock Entry Ledger Data Error')
        frappe.throw(f"An error occurred: {str(e)}")
