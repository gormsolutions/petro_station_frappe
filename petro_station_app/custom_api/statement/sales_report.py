import frappe
from frappe.model.document import Document

@frappe.whitelist()
def fetch_and_aggregate_station_shift_data(station, date=None):
    # Fetch all Station Shift Management records for the given date, station, and ensure the record is not canceled
    station_shift_records = frappe.get_all(
        'Station Shift Management', 
        filters={
            'from_date': date, 
            'docstatus': ['in', [0, 1]],  # Include drafts (docstatus=0) and submitted (docstatus=1)
            'station': station, 
            'status': ['!=', 'Cancelled']
        },
        fields=['name', 'from_date', 'docstatus', 'station', 'shift', 'employe_name', 'status']
    )

    # List to store individual entries of pump_or_tank for each shift and employee
    pump_or_tank_entries = []

    # Iterate through each record
    for record in station_shift_records:
        employee_name = record['employe_name']  # Extract employee name from the record
        shift = record['shift']
        docstatus = record['docstatus']

        # Fetch the items (child table) related to the Station Shift Management record
        items = frappe.get_all(
            'Station Shift Management item', 
            filters={'parent': record['name']},
            fields=['pump_or_tank', 'opening_meter_reading', 
                    'closing_meter_reading', 'qty_sold_on_meter_reading',
                    'qty_based_on_sales', 'sales_based_on_meter_reading',
                    'sales_based_on_invoices', 'difference_amount']
        )

        # Process items for the current shift
        for item in items:
            pump_or_tank_entry = {
                'pump_or_tank': item['pump_or_tank'],
                'employee_name': employee_name,
                'docstatus': docstatus,
                'shift': shift,
                'opening_meter_reading': item['opening_meter_reading'],
                'closing_meter_reading': item['closing_meter_reading'],
                'qty_sold_on_meter_reading': item['qty_sold_on_meter_reading'],
                'qty_based_on_sales': item['qty_based_on_sales'],
                'sales_based_on_meter_reading': item['sales_based_on_meter_reading'],
                'sales_based_on_invoices': item['sales_based_on_invoices'],
                'difference_amount': item['difference_amount']
            }
            pump_or_tank_entries.append(pump_or_tank_entry)

    # Return the list of pump_or_tank entries showing both shifts and respective employees
    return {
        "message": "Processed Station Shift records successfully.",
        "pump_or_tank_entries": pump_or_tank_entries
    }


import frappe
@frappe.whitelist()
def has_management_role():
    # Get the roles of the logged-in user
    roles = frappe.get_roles()
    
    # Check if "Management Role" is in the user's roles
    if "Management Role" in roles:
        return True
    return False

