import frappe

@frappe.whitelist()
def get_station_shift_management_records(employee_name=None, station=None, date=None):
    try:
        # Build the filters dictionary based on the provided parameters
        filters = {}
        if employee_name:
            filters["employee"] = employee_name
        if station:
            filters["station"] = station
        if date:
            filters["from_date"] = date

        # Fetch the Station Shift Management documents with filters
        records = frappe.db.get_all(
            'Station Shift Management',
            fields=['name', 'employee', 'from_date', 'station'],
            filters=filters,
            order_by="from_date desc"
        )

        # Process each document to fetch child table data
        for record in records:
            # Fetch child table data (items)
            items = frappe.db.get_all(
                'Station Shift Management item',
                filters={'parent': record['name']},
                fields=['pump_or_tank']
            )
            # Trim the suffix '- SE' from pump_or_tank if present
            for item in items:
                if item.get('pump_or_tank') and '- SE' in item['pump_or_tank']:
                    item['pump_or_tank'] = item['pump_or_tank'].replace('- SE', '').strip()

            record['items'] = items

        return records
    except Exception as e:
        frappe.log_error(message=str(e), title="Fetch Station Shift Management Records Error")
        return {"error": str(e)}
