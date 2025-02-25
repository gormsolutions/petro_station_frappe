import frappe

@frappe.whitelist()
def get_detailed_totals(posting_date, cost_center):
    # Ensure both posting_date and cost_center are provided
    if not posting_date or not cost_center:
        frappe.throw("Both posting_date and cost_center are required.")
    
    filters = {
        "posting_date": posting_date,
        "cost_center": cost_center
    }
    
    purchase_data = frappe.db.sql(f"""
    SELECT 
        pi.supplier, 
        pii.item_code, 
        pii.warehouse,
        pr.warehouse as tank, 
        SUM(pii.qty) AS total_qty,  -- Summing quantity
        SUM(pi.grand_total) AS total_grand_total,  -- Summing grand total for grouped records
        SUM(pi.outstanding_amount) AS total_outstanding_amount  -- Summing outstanding amounts
    FROM `tabPurchase Invoice` pi
    JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
    JOIN `tabPurchase Receipt Item` pr ON pii.purchase_receipt = pr.parent 
    WHERE 
        pi.docstatus = 1  -- Only include submitted invoices
        AND pi.posting_date = %(posting_date)s
        AND pi.cost_center = %(cost_center)s
    GROUP BY pi.supplier, pii.item_code, pr.warehouse
    """, filters, as_dict=True)

    
    # GL Entry Details (Cash Accounts)
    gl_entries = frappe.db.sql(f"""
        SELECT gle.account, acc.account_type, SUM(debit - credit) as balance
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE acc.account_type IN ('Cash', 'Bank','Receivable')
        AND gle.posting_date = %(posting_date)s
        AND gle.cost_center = %(cost_center)s
        AND gle.is_cancelled = 0  -- Exclude cancelled GL Entries
        GROUP BY gle.account, acc.account_type
    """, filters, as_dict=True)
    
    journal_entries = frappe.db.sql(f"""
    SELECT name, SUM(total_debit) / 2 AS half_total_debit
    FROM `tabJournal Entry`
    WHERE docstatus = 1  -- Only include submitted journal entries
    AND posting_date = %(posting_date)s
    AND custom_cost_center = %(cost_center)s
    AND (
        (custom_fuel_expense_id IS NOT NULL AND custom_fuel_expense_id != '') 
        OR (custom_station_expense_id IS NOT NULL AND custom_station_expense_id != '')
    )
""", filters, as_dict=True)


    # Sales Invoice Details
    sales_data = frappe.db.sql(f"""
    SELECT 
        si.customer, 
        sii.item_code, 
        wh.default_in_transit_warehouse as tank, 
        SUM(sii.qty) AS total_qty,  -- Summing quantity
        SUM(si.grand_total) AS total_grand_total,  -- Summing grand total for grouped records
        SUM(si.outstanding_amount) AS total_outstanding_amount  -- Summing outstanding amounts
    FROM `tabSales Invoice` si
    JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    JOIN `tabWarehouse` wh ON sii.warehouse = wh.name  -- Corrected join condition
    WHERE si.docstatus = 1  -- Only include submitted invoices
    AND si.posting_date = %(posting_date)s
    AND si.cost_center = %(cost_center)s
    AND customer NOT IN ('Annex Cash Customer', 'Sal Oil Cash Customer', 'Sal Cash Customer', 
                          'Shell cash customer', 'Cash Customer', 'Mobile App Cash Customer')
    GROUP BY si.customer, sii.item_code, wh.default_in_transit_warehouse
""", filters, as_dict=True)

    
    # Payment Entry Details
    payment_entries = frappe.db.sql(f"""
        SELECT payment_type, party, paid_amount, paid_to
        FROM `tabPayment Entry`
        WHERE payment_type IN ('Receive', 'Pay')
        AND docstatus != 0  -- Exclude drafts
        AND docstatus != 2  -- Exclude cancelled
        AND posting_date = %(posting_date)s
        AND cost_center = %(cost_center)s
        AND party NOT IN ('Annex Cash Customer', 'Sal Oil Cash Customer', 'Sal Cash Customer', 
                          'Shell cash customer', 'Cash Customer', 'Mobile App Cash Customer')
    """, filters, as_dict=True)
    
    # Payment Entry Details
    payway = frappe.db.sql(f"""
        SELECT amount as Amount,lebeled_name
        FROM `tabPAYWAY`
        WHERE docstatus != 0  -- Exclude drafts
        AND docstatus != 2  -- Exclude cancelled
        AND date = %(posting_date)s
        AND station = %(cost_center)s
    """, filters, as_dict=True)


    # Dipping Log Details (Tank Activity)
    dipping_logs = frappe.db.sql("""
        SELECT tank, SUM(current_acty_qty) as total_activity_qty, current_dipping_level, 
               SUM(dipping_difference) as total_dipping_difference
        FROM `tabDipping Log`
        WHERE dipping_date = DATE_ADD(%(posting_date)s, INTERVAL 1 DAY)  -- Fetch records for the next day
        AND branch = %(cost_center)s
        AND docstatus NOT IN (0, 2)  -- Exclude drafts and cancelled
        GROUP BY tank
    """, filters, as_dict=True)

    
    qty_sold_data = frappe.db.sql(f"""
    SELECT 
        si.posting_date, 
        sii.item_code, 
        wh.default_in_transit_warehouse AS tank, 
        SUM(sii.qty) AS total_qty_sold  -- Sum of sold quantity per item per date
    FROM `tabSales Invoice` si
    JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    JOIN `tabWarehouse` wh ON sii.warehouse = wh.name  -- Ensure proper warehouse join
    JOIN `tabItem` i ON sii.item_code = i.item_code  -- Join to filter by item group
    WHERE si.docstatus = 1  -- Only include submitted invoices
    AND si.posting_date = %(posting_date)s
    AND si.cost_center = %(cost_center)s
    AND i.item_group = 'Fuel'  -- Filter only Fuel items
    GROUP BY si.posting_date, sii.item_code, wh.default_in_transit_warehouse
""", filters, as_dict=True)
   
    return {
        "gl_entries": gl_entries,
        "journal_entries": journal_entries,
        "sales_data": sales_data,
        "payment_entries": payment_entries,
        "dipping_logs": dipping_logs,
        "total_qty_sold":qty_sold_data,
        "purchase_data":purchase_data,
        "payway":payway
    }
