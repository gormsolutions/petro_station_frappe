import frappe

@frappe.whitelist()
def get_bins_for_station(current_user, item_group=None):
    # Fetch station records for the given user.
    station_records = frappe.get_all(
        "Stations",
        filters={"user": current_user},
        fields=["name"]
    )
    
    if not station_records:
        return []

    # If an item group filter is provided, fetch the list of items in that group.
    item_codes = []
    if item_group:
        items = frappe.get_all("Item", filters={"custom_item_category": item_group}, fields=["name"])
        item_codes = [item["name"] for item in items]
    
    bins_list = []
    
    # Iterate over each station and get its child table data.
    for station in station_records:
        station_doc = frappe.get_doc("Stations", station["name"])
        
        # Ensure there is child table data in combined_stations.
        if not station_doc.combined_stations:
            continue

        for child in station_doc.combined_stations:
            # Assuming the child table has a field 'station' to filter Warehouses.
            cost_center = child.station  # Adjust the field name if necessary.
            
            # Fetch warehouses matching the cost center and user.
            stores = frappe.get_all(
                "Warehouse",
                filters={"custom_cost_centre": cost_center, "custom_user": current_user},
                fields=["name"]
            )

            warehouse_names = [store["name"] for store in stores]
            if not warehouse_names:
                continue

            # Prepare filters for the Bin query.
            filters = {"warehouse": ["in", warehouse_names]}
            # If item_group is provided, filter bins by the fetched item_codes.
            if item_group:
                # If no items match the group, skip.
                if not item_codes:
                    continue
                filters["item_code"] = ["in", item_codes]

            bins = frappe.get_all(
                "Bin",
                filters=filters,
                fields=["name", "warehouse", "item_code", "actual_qty"]
            )

            bins_list.extend(bins)

    return bins_list


import frappe

@frappe.whitelist()
def get_all_users():
    """
    Fetch all active users in Frappe.
    """
    users = frappe.get_all(
        "User",
        filters={"enabled": 1},  # Only fetch active users
        fields=["name", "full_name", "email", "role_profile_name"]
    )
    return users
