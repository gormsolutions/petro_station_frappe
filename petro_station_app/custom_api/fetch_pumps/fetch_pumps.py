import json
import frappe
from frappe import _

@frappe.whitelist()
def get_pump_or_tank(employee, date=None, shift=None, station=None):
    try:
        # Check if any of the parameters are None and handle accordingly
        if not employee:
            frappe.throw(_("Employee is required"))
        if not date:
            frappe.throw(_("Date is required"))
        if not shift:
            frappe.throw(_("Shift is required"))
        if not station:
            frappe.throw(_("Station is required"))
        
        # Sanitize inputs by stripping leading/trailing spaces (after checking they're not None)
        employee = employee.strip() if employee else None
        date = date.strip() if date else None
        shift = shift.strip() if shift else None
        station = station.strip() if station else None

        # Fetch the distinct pump_or_tank values and their associated qty_sold_on_meter_reading
        pump_or_tank_values = frappe.db.sql(
            """
            SELECT DISTINCT 
                shift_item.pump_or_tank,
                shift_item.qty_sold_on_meter_reading
            FROM 
                `tabStation Shift Management item` AS shift_item
            JOIN 
                `tabStation Shift Management` AS shift_doc
            ON 
                shift_item.parent = shift_doc.name
            WHERE 
                shift_doc.from_date = %(date)s
                AND shift_doc.station = %(station)s
                AND shift_doc.employee = %(employee)s
                AND shift_doc.shift = %(shift)s
            """,
            {
                'date': date,  # Date has already been stripped
                'employee': employee,  # Employee has already been stripped
                'shift': shift,  # Shift has already been stripped
                'station': station  # Station has already been stripped
            },
            as_dict=True
        )

        # Validate and return the results
        return [
            {
                "pump_or_tank": row.get("pump_or_tank"),
                "qty_sold_on_meter_reading": row.get("qty_sold_on_meter_reading")
            }
            for row in pump_or_tank_values
        ]

    except json.JSONDecodeError as e:
        frappe.throw(_("Invalid JSON in filters: {0}").format(str(e)))

    except frappe.db.ProgrammingError as e:
        frappe.throw(_("SQL Error: {0}").format(str(e)))

    except Exception as e:
        frappe.throw(_("An unexpected error occurred: {0}").format(str(e)))



import frappe
from frappe import _
import json
from datetime import datetime

@frappe.whitelist()
def get_total_qty(station, from_date, pump_or_tank_list, employee=None, status=None):
    total_qty = 0

    # Convert pump_or_tank_list from JSON string to Python list if necessary
    if isinstance(pump_or_tank_list, str):
        pump_or_tank_list = json.loads(pump_or_tank_list)

    filters = {
        "docstatus": 1,
        "posting_date": from_date,
    }

    if status:
        filters["status"] = status
        
    if employee:
        filters["custom_employee"] = employee

    # Aggregate Sales Invoice data
    sales_invoices = frappe.get_list(
        "Sales Invoice",
        filters=filters,
        fields=["name"]
    )

    for invoice in sales_invoices:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice.name)
        has_matching_item = any(item.cost_center == station for item in invoice_doc.items)

        if has_matching_item:
            for item in invoice_doc.items:
                if item.cost_center == station and item.warehouse in pump_or_tank_list:
                    total_qty += item.qty

    # Aggregate Stock Entry data
    stock_entries = frappe.get_list(
        "Stock Entry",
        filters={"stock_entry_type": "Material Transfer", "posting_date": from_date, "docstatus": 1},
        fields=["name"]
    )

    for stock_entry in stock_entries:
        stock_entry_doc = frappe.get_doc("Stock Entry", stock_entry.name)
        for item in stock_entry_doc.items:
            source_warehouse_doc = frappe.get_doc("Warehouse", item.s_warehouse)
            if source_warehouse_doc.warehouse_type == "Pump":
                for warehouse_type in ['s_warehouse', 't_warehouse']:
                    warehouse = getattr(item, warehouse_type)
                    if warehouse in pump_or_tank_list:
                        total_qty += item.qty

    return total_qty
