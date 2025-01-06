import frappe
from frappe.model.document import Document

@frappe.whitelist()
def fetch_and_aggregate_station_shift_data(date, station):
    # Fetch all Station Shift Management records for the given date and station
    station_shift_records = frappe.get_all('Station Shift Management', filters={'from_date': date, 'station_point': station}, fields=['name', 'from_date', 'station_point'])

    # Dictionary to store aggregated totals for each pump_or_tank
    totals_by_pump_or_tank = {}

    # Iterate through each record
    for record in station_shift_records:
        # Fetch the items (child table) related to the Station Shift Management record
        items = frappe.get_all('Station Shift Management item', filters={'parent': record['name']},
                               fields=['pump_or_tank', 'opening_meter_reading', 
                                       'closing_meter_reading',
                                       'qty_sold_on_meter_reading','qty_based_on_sales',
                                       'sales_based_on_meter_reading','sales_based_on_invoices',
                                       'difference_amount'])

        # Process items to aggregate based on pump_or_tank
        for item in items:
            key = item['pump_or_tank']
            if key not in totals_by_pump_or_tank:
                totals_by_pump_or_tank[key] = {'opening_meter_reading': 0,
                                               'closing_meter_reading': 0,
                                               'qty_sold_on_meter_reading': 0,
                                               'qty_based_on_sales': 0,
                                               'sales_based_on_meter_reading': 0,
                                               'sales_based_on_invoices': 0,
                                                'difference_amount': 0,
                                            
                                               
                                               }

            # Aggregate values
            totals_by_pump_or_tank[key]['opening_meter_reading'] += item['opening_meter_reading']
            totals_by_pump_or_tank[key]['closing_meter_reading'] += item['closing_meter_reading']
            totals_by_pump_or_tank[key]['qty_sold_on_meter_reading'] += item['qty_sold_on_meter_reading']
            totals_by_pump_or_tank[key]['qty_based_on_sales'] += item['qty_based_on_sales']
            totals_by_pump_or_tank[key]['sales_based_on_meter_reading'] += item['sales_based_on_meter_reading']
            totals_by_pump_or_tank[key]['sales_based_on_invoices'] += item['sales_based_on_invoices']
            totals_by_pump_or_tank[key]['difference_amount'] += item['difference_amount']

        # # Now, update the Station Shift Management record with aggregated values for that date
        # for pump_or_tank, values in totals_by_pump_or_tank.items():
        #     # Create or update the corresponding child table items with the aggregated readings
        #     update_station_shift_item(record['name'], pump_or_tank, values)

    # Return the aggregated totals for each pump_or_tank
    return {
        "message": "Processed Station Shift records successfully.",
        "totals_by_pump_or_tank": totals_by_pump_or_tank
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
