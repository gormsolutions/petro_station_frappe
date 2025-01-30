import frappe

@frappe.whitelist()
def get_fuel_transit_stock_qty(cost_center=None):
    # Base query
    query = """
        SELECT 
            bin.item_code, 
            bin.warehouse, 
            bin.actual_qty,
            bin.valuation_rate,
            warehouse.custom_tank_fuel_copacity
        
        FROM 
            `tabBin` AS bin
        JOIN 
            `tabItem` AS item ON bin.item_code = item.name
        JOIN 
            `tabWarehouse` AS warehouse ON bin.warehouse = warehouse.name
        WHERE 
            item.item_group = %s
            AND warehouse.warehouse_type = %s
    """
    # Parameters for the query
    params = ['Fuel', 'Transit']

    # Add an optional filter for cost_center if provided
    if cost_center:
        query += " AND warehouse.custom_cost_centre = %s"
        params.append(cost_center)

    # Execute the query
    stock_qty = frappe.db.sql(query, params, as_dict=True)
    
    return stock_qty

@frappe.whitelist()
def reset_password_and_update_image(new_password=None, image_url=None):
    try:
        # Get the logged-in user's email
        user_email = frappe.session.user
        
        # Fetch the user document
        user = frappe.get_doc("User", user_email)
        
        # Reset the password if provided
        if new_password:
            frappe.utils.password.update_password(user_email, new_password)
        
        # Update the profile image if provided
        if image_url:
            user.user_image = image_url
            user.save()
        else:
            # Save the user document even if no updates are made
            user.save()

        frappe.db.commit()  # Commit the transaction

        # Dynamic success message
        message = f"User: {user_email} updated successfully."
        if new_password:
            message += " Password reset completed."
        if image_url:
            message += " Profile image updated."

        return {
            "status": "success",
            "message": message
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"User with email {user_email} does not exist"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

import frappe

@frappe.whitelist()
def get_user_doc():
    try:
        # Get the logged-in user's email
        user_email = frappe.session.user

        # Fetch the User document
        user_doc = frappe.get_doc("User", user_email)

        # Convert the document to a dictionary for API response
        user_data = user_doc.as_dict()

        # Return the user document
        return {
            "status": "success",
            "user_data": user_data
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "User does not exist"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }
