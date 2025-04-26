from datetime import datetime
import frappe

@frappe.whitelist()
def save_station_shift_management():
    try:
        # Parse data from the request
        data = frappe.form_dict.get("data")
        if isinstance(data, str):
            data = frappe.parse_json(data)

        # Extract and validate fields
        from_date = data.get("from_date")
        if not from_date:
            frappe.throw("The 'from_date' field is required.")
        
        # Ensure the date is in the correct format (YYYY-MM-DD)
        try:
            from_date = datetime.strptime(from_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            frappe.throw("The 'from_date' field must be in the format YYYY-MM-DD.")

        # Ensure other required fields are provided
        employee = data.get("employee")
        if not employee:
            frappe.throw("The 'employee' field is required.")

        shift = data.get("shift")
        if not shift:
            frappe.throw("The 'shift' field is required.")

        # Handle items (ensure they are properly formatted)
        items = data.get("items", [])
        if not items:
            frappe.throw("At least one item must be provided.")
        
        # Check if the document already exists
        existing_doc = frappe.get_all(
            "Station Shift Management", 
            filters={"employee": employee, "shift": shift, "from_date": from_date},
            limit_page_length=1
        )

        if existing_doc:
            # Fetch the existing document
            station_shift_management = frappe.get_doc("Station Shift Management", existing_doc[0].name)

            # Update the items, closing_meter_reading, and qty_sold_on_meter_reading in the existing document
            for item in items:
                # Find the corresponding item in the existing document
                for existing_item in station_shift_management.items:
                    if existing_item.pump_or_tank == item.get("pump_or_tank"):
                        # Update closing_meter_reading and qty_sold_on_meter_reading
                        existing_item.closing_meter_reading = item.get("closing_meter_reading")
                        existing_item.qty_sold_on_meter_reading = item.get("diferent_meter_reading")  # Ensure this is updated
                        break
            # Save the updated document
            station_shift_management.save()
        else:
            # Creating the Station Shift Management document if it does not exist
            station_shift_management = frappe.get_doc({
                "doctype": "Station Shift Management",
                "employee": employee,
                "shift": shift,
                "from_date": from_date,
                "items": [
                    {
                        "pump_or_tank": item.get("pump_or_tank"),
                        "opening_meter_reading": item.get("opening_meter_reading"),
                        "closing_meter_reading": item.get("closing_meter_reading"),
                        "qty_sold_on_meter_reading": item.get("diferent_meter_reading"),
                    }
                    for item in items
                ],
            })

            # Insert and save the new document
            station_shift_management.insert()
        
        frappe.db.commit()

        # Fetch the saved document to return a response with relevant information
        saved_doc = frappe.get_doc("Station Shift Management", station_shift_management.name)
        return {
            "status": "success",
            "message": "Station Shift Management saved successfully.",
            "name": saved_doc.name,
            "items": saved_doc.items,
        }
    
    except frappe.ValidationError as ve:
        # Handling validation errors specifically
        frappe.log_error(frappe.get_traceback(), "Save Station Shift Management Validation Error")
        frappe.throw(f"Validation Error: {str(ve)}")
    
    except Exception as e:
        # General error handling
        frappe.log_error(frappe.get_traceback(), "Save Station Shift Management Error")
        frappe.throw(f"An error occurred while saving the data: {str(e)}")


import frappe
from frappe.utils import add_days
from collections import defaultdict

@frappe.whitelist()
def validate_previous_day_shifts(station, posting_date):
    current_user = frappe.session.user

    shift_closing_setting = frappe.get_value(
        "Shift Closing Setting",
        {"user": current_user, "station": station},
        "number_of_pumps"
    )

    if not shift_closing_setting:
        frappe.throw("<div style='font-size:14px;color:#b71c1c;'><strong>❌ No Shift Closing Setting configured for you as a user and station.</strong></div>")

    expected_pumps = int(shift_closing_setting)  # Ensure expected_pumps is an integer
    previous_day = add_days(posting_date, -1)

    submitted_shifts = frappe.get_all(
        "Station Shift Management",
        filters={
            "station": station,
            "docstatus": 1,
            "from_date": previous_day
        },
        fields=["name", "employee", "shift"]
    )

    draft_shifts = frappe.get_all(
        "Station Shift Management",
        filters={
            "station": station,
            "docstatus": 0,
            "from_date": previous_day
        },
        fields=["name", "employee", "shift"]
    )

    total_pumps_submitted = 0
    total_pumps_draft = 0
    pump_group_submitted = defaultdict(list)
    pump_group_draft = defaultdict(list)

    def get_employee_name(employee_id):
        if employee_id:
            return frappe.get_value("Employee", employee_id, "employee_name") or "N/A"
        return "N/A"

    for shift in submitted_shifts:
        pump_records = frappe.get_all(
            "Station Shift Management item",
            filters={"parent": shift.name, "pump_or_tank": ["!=", ""]},
            fields=["pump_or_tank", "employee_for_next_shift"]
        )
        total_pumps_submitted += len(pump_records)
        for p in pump_records:
            pump_group_submitted[shift.shift].append(
                f"{p['pump_or_tank']} — {get_employee_name(p['employee_for_next_shift'])}"
            )

    for shift in draft_shifts:
        pump_records = frappe.get_all(
            "Station Shift Management item",
            filters={"parent": shift.name, "pump_or_tank": ["!=", ""]},
            fields=["pump_or_tank", "employee_for_next_shift"]
        )
        total_pumps_draft += len(pump_records)
        for p in pump_records:
            pump_group_draft[shift.shift].append(
                f"{p['pump_or_tank']} — {get_employee_name(p['employee_for_next_shift'])}"
            )

    no_shift_created = not submitted_shifts and not draft_shifts

    def generate_grouped_html(grouped_data):
        if not grouped_data:
            return "<li>None</li>"
        html = ""
        for shift, records in grouped_data.items():
            html += f"<li><strong>{shift} Shift</strong><ul>"
            for record in records:
                html += f"<li>{record}</li>"
            html += "</ul></li>"
        return html

    message = f"""
    <div style="font-family:Arial, sans-serif; font-size:13px; line-height:1.6; color:#333;">
        <h3 style="margin:0 0 10px 0; color:#d32f2f;">🚨 Previous Day's Closure Validation</h3>
        <p><strong>📅 Date:</strong> {previous_day}</p>
        <p><strong>📌 Station:</strong> {station}</p>
        <p><strong>👤 User:</strong> {current_user}</p>

        <hr style="border:0; border-top:1px solid #ddd; margin:10px 0;"/>

        <p><strong>✅ Expected Pumps:</strong> {expected_pumps}</p>

        <p><strong>✔️ Submitted Pumps ({total_pumps_submitted}):</strong></p>
        <ul style="padding-left:18px; margin:5px 0;">
            {generate_grouped_html(pump_group_submitted)}
        </ul>

        <p><strong>📝 Draft Pumps ({total_pumps_draft}):</strong></p>
        <ul style="padding-left:18px; margin:5px 0;">
            {generate_grouped_html(pump_group_draft)}
        </ul>

        <hr style="border:0; border-top:1px solid #ddd; margin:10px 0;"/>

        {"<p style='color:#b71c1c;'><strong>❌ No Station Shift Management created at all for this date.</strong></p>" if no_shift_created else ""}
        {f"<p style='color:#b71c1c;'><strong>❗ Mismatch detected — Expected {expected_pumps}, but found {total_pumps_submitted} submitted.</strong></p>" if total_pumps_submitted != expected_pumps else ""}
        {f"<p style='color:#388e3c;'><strong>✅ All pumps are correctly submitted.</strong></p>" if total_pumps_submitted == expected_pumps else ""}
        
        {"<p style='color:#f57c00;'><strong>👉 Please finish closing the previous day's shifts before proceeding.</strong></p>" if total_pumps_submitted != expected_pumps else ""}
    </div>
    """

    # Only return a failure message if the pumps do not match "message": message,
    if total_pumps_submitted != expected_pumps:
        return {"status": False, "total_pumps_submitted": total_pumps_submitted, "expected_pumps": expected_pumps, "message": message}
    else:
        return {"status": True}
