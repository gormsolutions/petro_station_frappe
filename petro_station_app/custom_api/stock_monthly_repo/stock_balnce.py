# import frappe

# @frappe.whitelist()
# def fetch_sales_invoice_items_with_stock(company, cost_center=None, warehouse=None):
#     """Fetch all unique items from Sales Invoice along with their stock balance, times purchased, and times reconciled (Stock Reconciliation), 
#     grouped by item group, sorted by most sold items, filtered by company, cost center, and warehouse."""

#     # Step 1: Prepare the filter dictionary
#     filters = {"company": company}

#     # Step 2: Construct SQL query for Sales Invoice Items, including cost_center and warehouse filters
#     sales_invoice_items_sql = """
#         SELECT
#             sii.item_code,
#             SUM(sii.qty) AS total_qty_sold
#         FROM
#             `tabSales Invoice Item` sii
#         INNER JOIN
#             `tabSales Invoice` si ON sii.parent = si.name
#         WHERE
#             si.docstatus = 1  -- Only submitted Sales Invoices
#             AND si.company = %(company)s  -- Filter by company
#     """
    
#     if cost_center:
#         sales_invoice_items_sql += " AND sii.cost_center = %(cost_center)s"
#         filters["cost_center"] = cost_center
    
#     if warehouse:
#         sales_invoice_items_sql += " AND sii.warehouse = %(warehouse)s"
#         filters["warehouse"] = warehouse

#     sales_invoice_items_sql += """
#         GROUP BY
#             sii.item_code
#         ORDER BY
#             total_qty_sold DESC  -- Sort by most sold items
#     """

#     sales_invoice_items = frappe.db.sql(sales_invoice_items_sql, filters, as_dict=True)

#     if not sales_invoice_items:
#         frappe.msgprint("No items found in Sales Invoices for the selected company and filters.")
#         return {}

#     # Step 3: Fetch stock balance from Bin for these items filtered by company
#     item_codes = [item['item_code'] for item in sales_invoice_items]
#     items_with_stock_sql = """
#         SELECT
#             b.item_code,
#             SUM(b.actual_qty) AS total_qty
#         FROM
#             `tabBin` b
#         INNER JOIN
#             `tabWarehouse` w ON b.warehouse = w.name
#         WHERE
#             b.item_code IN %(item_codes)s
#             AND w.company = %(company)s  -- Filter by company
#     """
    
#     if warehouse:
#         items_with_stock_sql += " AND b.warehouse = %(warehouse)s"
    
#     items_with_stock_sql += """
#         GROUP BY
#             b.item_code
#     """
    
#     items_with_stock = frappe.db.sql(items_with_stock_sql, {"item_codes": item_codes, "company": company, "warehouse": warehouse}, as_dict=True)

#     # Step 4: Fetch item groups from the Item doctype
#     item_groups = {item['item_code']: frappe.get_value('Item', item['item_code'], 'item_group') for item in sales_invoice_items}

#     # Step 5: Fetch purchase counts (how many times each item was purchased)
#     purchase_counts_sql = """
#         SELECT
#             pi_item.item_code,
#             COUNT(pi_item.item_code) AS purchase_count
#         FROM
#             `tabPurchase Invoice Item` pi_item
#         INNER JOIN
#             `tabPurchase Invoice` pi ON pi_item.parent = pi.name
#         WHERE
#             pi.docstatus = 1  -- Only submitted Purchase Invoices
#             AND pi.company = %(company)s  -- Filter by company
#     """

#     if cost_center:
#         purchase_counts_sql += " AND pi_item.cost_center = %(cost_center)s"
    
#     purchase_counts_sql += """
#         GROUP BY
#             pi_item.item_code
#     """
    
#     purchase_counts = frappe.db.sql(purchase_counts_sql, {"company": company, "cost_center": cost_center}, as_dict=True)

#     purchase_count_dict = {item['item_code']: item['purchase_count'] for item in purchase_counts}

#     # Step 6: Fetch reconciliation counts (how many times each item was reconciled through Stock Reconciliation)
#     reconciliation_counts_sql = """
#         SELECT
#             sr_item.item_code,
#             COUNT(sr_item.item_code) AS reconciliation_count
#         FROM
#             `tabStock Reconciliation Item` sr_item
#         INNER JOIN
#             `tabStock Reconciliation` sr ON sr_item.parent = sr.name
#         WHERE
#             sr.docstatus = 1  -- Only submitted Stock Reconciliation entries
#             AND sr.company = %(company)s  -- Filter by company
#     """

#     if cost_center:
#         reconciliation_counts_sql += " AND sr.cost_center = %(cost_center)s"
    
#     reconciliation_counts_sql += """
#         GROUP BY
#             sr_item.item_code
#     """
    
#     reconciliation_counts = frappe.db.sql(reconciliation_counts_sql, {"company": company, "cost_center": cost_center}, as_dict=True)

#     reconciliation_count_dict = {item['item_code']: item['reconciliation_count'] for item in reconciliation_counts}

#     # Step 7: Group items by item_group, add stock balance, purchase count, and reconciliation count
#     grouped_items = {}
#     for item in sales_invoice_items:
#         item_code = item['item_code']
#         item_group = item_groups.get(item_code, "Uncategorized")  # Default to "Uncategorized" if no item group is found
#         item_stock = next((stock for stock in items_with_stock if stock['item_code'] == item_code), None)
#         purchase_count = purchase_count_dict.get(item_code, 0)
#         reconciliation_count = reconciliation_count_dict.get(item_code, 0)

#         if item_group not in grouped_items:
#             grouped_items[item_group] = []

#         grouped_items[item_group].append({
#             "item_code": item_code,
#             "total_qty_sold": item['total_qty_sold'],
#             "total_qty": item_stock['total_qty'] if item_stock else 0,
#             "purchase_count": purchase_count,
#             "reconciliation_count": reconciliation_count
#         })

#     return grouped_items

import frappe

@frappe.whitelist()
def fetch_sales_invoice_items_with_stock(company, cost_center=None, warehouse=None):
    """Fetch all unique items from Sales Invoice along with their stock balance and times reconciled (Stock Reconciliation), 
    grouped by item group, sorted by most sold items, filtered by company, cost center, and warehouse."""

    # Step 1: Prepare the filter dictionary
    filters = {"company": company}

    # Step 2: Construct SQL query for Sales Invoice Items, including cost_center and warehouse filters
    sales_invoice_items_sql = """
        SELECT
            sii.item_code,
            SUM(sii.qty) AS total_qty_sold
        FROM
            `tabSales Invoice Item` sii
        INNER JOIN
            `tabSales Invoice` si ON sii.parent = si.name
        WHERE
            si.docstatus = 1  -- Only submitted Sales Invoices
            AND si.company = %(company)s  -- Filter by company
    """
    
    if cost_center:
        sales_invoice_items_sql += " AND sii.cost_center = %(cost_center)s"
        filters["cost_center"] = cost_center
    
    if warehouse:
        sales_invoice_items_sql += " AND sii.warehouse = %(warehouse)s"
        filters["warehouse"] = warehouse

    sales_invoice_items_sql += """
        GROUP BY
            sii.item_code
        ORDER BY
            total_qty_sold DESC  -- Sort by most sold items
    """

    sales_invoice_items = frappe.db.sql(sales_invoice_items_sql, filters, as_dict=True)

    if not sales_invoice_items:
        frappe.msgprint("No items found in Sales Invoices for the selected company and filters.")
        return {}

    # Step 3: Fetch stock balance from Bin for these items filtered by company
    item_codes = [item['item_code'] for item in sales_invoice_items]
    items_with_stock_sql = """
        SELECT
            b.item_code,
            SUM(b.actual_qty) AS total_qty
        FROM
            `tabBin` b
        INNER JOIN
            `tabWarehouse` w ON b.warehouse = w.name
        WHERE
            b.item_code IN %(item_codes)s
            AND w.company = %(company)s  -- Filter by company
    """
    
    if warehouse:
        items_with_stock_sql += " AND b.warehouse = %(warehouse)s"
    
    items_with_stock_sql += """
        GROUP BY
            b.item_code
    """
    
    items_with_stock = frappe.db.sql(items_with_stock_sql, {"item_codes": item_codes, "company": company, "warehouse": warehouse}, as_dict=True)

    # Step 4: Fetch item groups from the Item doctype
    item_groups = {item['item_code']: frappe.get_value('Item', item['item_code'], 'item_group') for item in sales_invoice_items}

    # Step 5: Fetch total quantity purchased (total qty from Purchase Invoices) for each item
    purchase_qty_sql = """
        SELECT
            pi_item.item_code,
            SUM(pi_item.qty) AS total_qty_purchased
        FROM
            `tabPurchase Invoice Item` pi_item
        INNER JOIN
            `tabPurchase Invoice` pi ON pi_item.parent = pi.name
        WHERE
            pi.docstatus = 1  -- Only submitted Purchase Invoices
            AND pi.company = %(company)s  -- Filter by company
    """

    if cost_center:
        purchase_qty_sql += " AND pi_item.cost_center = %(cost_center)s"
    
    purchase_qty_sql += """
        GROUP BY
            pi_item.item_code
    """
    
    purchase_qty = frappe.db.sql(purchase_qty_sql, {"company": company, "cost_center": cost_center}, as_dict=True)

    purchase_qty_dict = {item['item_code']: item['total_qty_purchased'] for item in purchase_qty}

    # Step 6: Fetch the total quantity for Stock Reconciliation (excluding Opening Stock)
    stock_reconciliation_sql = """
        SELECT
            sr_item.item_code,
            SUM(sr_item.qty) AS total_qty_reconciled
        FROM
            `tabStock Reconciliation Item` sr_item
        INNER JOIN
            `tabStock Reconciliation` sr ON sr_item.parent = sr.name
        WHERE
            sr.docstatus = 1  -- Only submitted Stock Reconciliation entries
            AND sr.company = %(company)s  -- Filter by company
            AND sr.purpose != 'Opening Stock'  -- Exclude 'Opening Stock' purpose
    """

    if cost_center:
        stock_reconciliation_sql += " AND sr.cost_center = %(cost_center)s"
    
    stock_reconciliation_sql += """
        GROUP BY
            sr_item.item_code
    """

    stock_reconciliation = frappe.db.sql(stock_reconciliation_sql, {"company": company, "cost_center": cost_center}, as_dict=True)

    stock_reconciliation_dict = {item['item_code']: item['total_qty_reconciled'] for item in stock_reconciliation}

    # Step 7: Fetch the total quantity for Opening Stock
    opening_stock_sql = """
        SELECT
            sr_item.item_code,
            SUM(sr_item.qty) AS total_qty_opening
        FROM
            `tabStock Reconciliation Item` sr_item
        INNER JOIN
            `tabStock Reconciliation` sr ON sr_item.parent = sr.name
        WHERE
            sr.docstatus = 1  -- Only submitted Stock Reconciliation entries
            AND sr.purpose = 'Opening Stock'  -- Filter by purpose 'Opening Stock'
            AND sr.company = %(company)s  -- Filter by company
    """

    if cost_center:
        opening_stock_sql += " AND sr.cost_center = %(cost_center)s"
    
    opening_stock_sql += """
        GROUP BY
            sr_item.item_code
    """

    opening_stock = frappe.db.sql(opening_stock_sql, {"company": company, "cost_center": cost_center}, as_dict=True)

    opening_stock_dict = {item['item_code']: item['total_qty_opening'] for item in opening_stock}

    # Step 8: Group items by item_group, add stock balance, total quantity purchased, opening stock, and stock reconciliation quantities
    grouped_items = {}
    for item in sales_invoice_items:
        item_code = item['item_code']
        item_group = item_groups.get(item_code, "Uncategorized")  # Default to "Uncategorized" if no item group is found
        item_stock = next((stock for stock in items_with_stock if stock['item_code'] == item_code), None)
        total_qty_purchased = purchase_qty_dict.get(item_code, 0)
        total_qty_reconciled = stock_reconciliation_dict.get(item_code, 0)
        total_qty_opening = opening_stock_dict.get(item_code, 0)

        if item_group not in grouped_items:
            grouped_items[item_group] = []

        grouped_items[item_group].append({
            "item_code": item_code,
            "total_qty_sold": item['total_qty_sold'],
            "total_qty_stock": item_stock['total_qty'] if item_stock else 0,
            "total_qty_purchased": total_qty_purchased,
            "total_qty_opening": total_qty_opening,  # Include the opening stock quantity
            "total_qty_reconciled": total_qty_reconciled  # Include the reconciled stock quantity
        })

    return grouped_items
