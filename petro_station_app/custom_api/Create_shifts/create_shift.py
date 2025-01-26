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
