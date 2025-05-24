import frappe

@frappe.whitelist()
def get_shift_details(doc,price_list):
    # Ensure the input doc is properly parsed
    if isinstance(doc, str):
        doc = frappe.get_doc(frappe.parse_json(doc))

    # Object to hold grouped totals by fuel
    shift_details = {}

    # Loop through 'items' child table
    for row in doc.get('items') or []:
        pump_or_tank = row.pump_or_tank

        # Fetch the fuel from the linked Warehouse
        fuel = frappe.db.get_value('Warehouse', pump_or_tank, 'custom_tank_item')
        if not fuel:
            fuel = 'Unknown Fuel'  # Handle cases where fuel might be missing

        # Fetch the item price from the default price list (e.g., 'Standard Selling')
        rate = frappe.db.get_value(
            'Item Price', 
            {'item_code': fuel, 'price_list': price_list}, 
            'price_list_rate'
        ) or 0

        # Grouping by fuel
        if fuel not in shift_details:
            # Initialize the entry for this fuel if not already present
            shift_details[fuel] = {
                'fuel': fuel,
                'opening_grand_total': 0,
                'closing_grand_total': 0,
                'qty_on_meter': 0,
                'qty_on_sales': 0,
                'rate': rate  # Include the item price as rate
            }

        # Add the values to the existing entry for this fuel
        shift_details[fuel]['opening_grand_total'] += row.opening_meter_reading
        shift_details[fuel]['closing_grand_total'] += row.closing_meter_reading
        shift_details[fuel]['qty_on_meter'] += row.qty_sold_on_meter_reading
        shift_details[fuel]['qty_on_sales'] += row.qty_based_on_sales

    # Return the aggregated shift details grouped by fuel
    return shift_details


@frappe.whitelist()
def get_shift_details_mobilewarehouse(doc,price_list):
    # Ensure the input doc is properly parsed
    if isinstance(doc, str):
        doc = frappe.get_doc(frappe.parse_json(doc))

    # Object to hold grouped totals by fuel
    shift_details = {}

    # Loop through 'items' child table
    for row in doc.get('mobile_warehouse_items') or []:
        pump_or_tank = row.mw_plate_number

        # Fetch the fuel from the linked Warehouse
        fuel = frappe.db.get_value('Warehouse', pump_or_tank, 'custom_tank_item')
        if not fuel:
            fuel = 'Unknown Fuel'  # Handle cases where fuel might be missing

        # Fetch the item price from the default price list (e.g., 'Standard Selling')
        rate = frappe.db.get_value(
            'Item Price', 
            {'item_code': fuel, 'price_list': price_list}, 
            'price_list_rate'
        ) or 0

        # Grouping by fuel
        if fuel not in shift_details:
            # Initialize the entry for this fuel if not already present
            shift_details[fuel] = {
                'fuel': fuel,
                'opening_grand_total': 0,
                'closing_grand_total': 0,
                'qty_on_meter': 0,
                'qty_on_sales': 0,
                'rate': rate  # Include the item price as rate
            }

        # Add the values to the existing entry for this fuel
        shift_details[fuel]['opening_grand_total'] += row.opening_quantity
        shift_details[fuel]['closing_grand_total'] += row.closing_quantity
        shift_details[fuel]['qty_on_meter'] += row.difference_on_opening_and_closing_quantit
        shift_details[fuel]['qty_on_sales'] += row.quantity_based_on_sales

    # Return the aggregated shift details grouped by fuel
    return shift_details

import frappe

@frappe.whitelist()
def get_shift_dippings(doc):
    # Ensure the input doc is properly parsed
    if isinstance(doc, str):
        doc = frappe.get_doc(frappe.parse_json(doc))

    # Object to hold grouped totals by fuel
    shift_details = {}

    # Loop through 'items' child table
    for row in doc.get('dipping_details') or []:
        pump_or_tank = row.tank

        # Fetch the fuel from the linked Warehouse
        fuel = frappe.db.get_value('Warehouse', pump_or_tank, 'custom_tank_item')
        if not fuel:
            fuel = 'Unknown Fuel'  # Handle cases where fuel might be missing

        # Grouping by fuel
        if fuel not in shift_details:
            # Initialize the entry for this fuel if not already present
            shift_details[fuel] = {
                'fuel': fuel,
                'dipping_qty': 0,
                'current_qty': 0,
                'amount_difference': 0,
                'quantity_difference': 0
            }

        # Add the values to the existing entry for this fuel
        shift_details[fuel]['dipping_qty'] += row.dipping_qty
        shift_details[fuel]['current_qty'] += row.current_qty
        shift_details[fuel]['amount_difference'] += row.amount_difference
        shift_details[fuel]['quantity_difference'] += row.quantity_difference

    # Return the aggregated shift details grouped by fuel
    return shift_details

