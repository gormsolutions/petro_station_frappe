from frappe.model.document import Document
import frappe
from frappe.utils import add_days, today
from frappe import _


class StationShiftManagement(Document):
    def on_submit(self):
        
        if not self.overal_shift_closing_items:
            
                # Throw an error if the overal_shift_closing_items is not there
            frappe.throw(
                f"Get Overall Shift Details before submiting the Shift."
            )
        # Define the tolerance limit
        tolerance = 1000
        
        
        # Calculate the difference
        difference = abs(self.meter_based_grand_total_amount - self.total_sales)

        # Check if the difference is within tolerance
        # if difference > tolerance:
        #     # Throw an error if the difference exceeds the tolerance
        #     frappe.throw(
        #         f"Meter Based Grand Total Amount ({self.meter_based_grand_total_amount}) must be within {tolerance} of Total Sales ({self.total_sales}). Difference: {difference}."
        #     )
        
        if self.items:
            self.create_next_shift()

        # self.take_dipping_before()
 
        # Fetch all transit warehouses
        transit_warehouses = frappe.get_all(
            "Warehouse",
            filters={"warehouse_type": "Transit"},
            fields=["name"]
        )

        # Extract list of transit warehouse names
        transit_warehouse_names = [wh['name'] for wh in transit_warehouses]

        # Fetch Stock Entry records that are drafts (docstatus 0) and of type 'Material Transfer'
        stock_entries = frappe.get_list(
            'Stock Entry',
            filters={'stock_entry_type': 'Material Transfer', 'docstatus': 0},
            fields=['name', 'posting_date', 'posting_time', 'stock_entry_type', 'docstatus'],
            order_by='posting_date desc'
        )
        
        # Check if any Stock Entry Details match the station and transit warehouse criteria
        for entry in stock_entries:
            stock_entry_details_drafts = frappe.get_all(
                'Stock Entry Detail',
                filters={
                    'parent': entry.name,
                    'docstatus': 0,  # Draft status
                    'cost_center': self.station,  # Check for matching station cost center
                    's_warehouse': ['in', transit_warehouse_names],  # Source must be transit warehouse
                    't_warehouse': ['in', transit_warehouse_names]   # Target must be transit warehouse
                },
                fields=['name', 'item_code', 's_warehouse', 't_warehouse', 'qty', 'cost_center']
            )

            # If drafts are found, raise an error
            if stock_entry_details_drafts:
                frappe.throw(f"You still haven't Recieved some draft stock entries for station {self.station}. Please complete them before proceeding.")
        
        

    def before_save(self):
        if self.from_date and self.station:
            # Check if a document already exists for the same date, employee, and shift, excluding the current document
            existing_doc = frappe.db.exists(
            'Station Shift Management',
            {
                'station': self.station,
                'from_date': self.from_date,
                'employee': self.employee,
                'shift': self.shift,
                'name': ['!=', self.name],  # Exclude the current document
                'docstatus': ['in', [0, 1]]  # Consider only Draft and Submitted documents
            }
        )

            # Debug message for checking the existing document
            # frappe.msgprint(f"Validating shift for employee {self.employee} on {self.from_date}.")

            # If a document exists, raise an exception
            if existing_doc:
                frappe.throw(
                    f"A shift management document already exists for station {self.station} on {self.from_date} for the same shift and employee."
                )



    def take_dipping_before(self):
       # Check if a Stock Reconciliation document exists for the same date and station
        if self.from_date and self.station:
            existing_doc = frappe.db.exists(
                'Stock Reconciliation',
                {
                    'posting_date': self.from_date,
                    'cost_center': self.station,
                    'purpose': "Stock Reconciliation",
                    'docstatus': 1  # docstatus 1 means the document is submitted
                }
            )

            if not existing_doc:  # Correcting the syntax for "not"
                frappe.throw(f"Dipping Levels should be taken for today before proceeding for station {self.station} on {self.from_date}.")
   
    def get_material_transfer_entries(self):
        try:
            # Fetch Stock Entry records with the required filters
            stock_entries = frappe.get_list('Stock Entry',
                filters={
                    'stock_entry_type': 'Material Transfer',
                    'docstatus': 0,  # Draft status
                    # 'posting_date':self.from_date
                },
                fields=['name', 'posting_date', 'posting_time', 'stock_entry_type', 'docstatus'],
                order_by='posting_date desc'
            )
            # Get warehouses with the specified cost center and warehouse types (Transit)
            transit_warehouses = frappe.get_all(
                "Warehouse",
                filters={
                    "warehouse_type": "Transit",
                    # "custom_cost_centre": station,
                },
                fields=["name"]
            )

            # Extract list of transit warehouse names
            transit_warehouse_names = [wh['name'] for wh in transit_warehouses]

            # Filter further to check for cost center in Stock Entry Detail child table
            filtered_entries = []
            for entry in stock_entries:
                stock_entry_details = frappe.get_all('Stock Entry Detail',
                    filters={
                        'parent': entry.name,
                        'cost_center': self.station,  # Filter by cost center == station
                        's_warehouse': ['in', transit_warehouse_names],  # Source warehouse must be of type Transit
                        't_warehouse': ['in', transit_warehouse_names]   # Target warehouse must be of type Transit
                    },
                    fields=['name', 'item_code', 's_warehouse', 't_warehouse', 'qty', 'cost_center']
                )

            if stock_entry_details:
                filtered_entries.append({
                    'stock_entry': entry.name,
                    'posting_date': entry.posting_date,
                    'status': entry.docstatus,
                    'posting_time': entry.posting_time,
                    'details': stock_entry_details
                })

            if filtered_entries:
                frappe.throw(f"Fuel Transfer should be done for today before proceeding for station {self.station} on {self.from_date}.")
         
  
        except Exception as e:
            # Log error if any and return error response
            frappe.log_error(frappe.get_traceback(), "Stock Entry Fetch Error")
            return {"status": "failed", "error": str(e)}

 
   
 
    # def on_update(self):
    #     self.create_next_shift()
   
    def create_next_shift(self):
        try:
            # Determine the next shift and date
            next_shift = "Night" if self.shift == "Day" else "Day"
            next_date = self.from_date if self.shift == "Day" else add_days(self.from_date, 1)

            # Debug: Log the current from_date
            # frappe.log_error(f"Current from_date: {self.from_date}", "Shift Debug")

            # Ensure items are present to process Throws the error only when: self.items is empty or None, AND
            # self.mobile_warehouse_items is not empty
            if not self.items and self.mobile_warehouse_items:
                frappe.throw(_("No items found to map for the next shift."))

            # Group rows by employee_for_next_shift
            employee_groups = {}
            for row in self.items:
                if not row.employee_for_next_shift:
                    frappe.throw(_("The employee for the next shift is mandatory for pump or tank {0}. Please set the employee for the next shift.")
                             .format(row.pump_or_tank))
                employee_groups.setdefault(row.employee_for_next_shift, []).append(row)

            # Process each unique employee
            for employee, rows in employee_groups.items():
            # Check if a shift already exists for this employee, date, and shift,
            # and also get the docstatus.
                existing_shift_data = frappe.db.get_value(
                    "Station Shift Management",
                    {"from_date": next_date, "shift": next_shift, "employee": employee},
                    ["name", "docstatus"],
                    as_dict=True
                )

                if existing_shift_data:
                # Only update if the existing shift is still a draft (docstatus == 0)
                    if existing_shift_data.docstatus != 0:
                        # frappe.log_error(
                        #     f"Existing shift for employee {employee} on {next_date} is not a draft (docstatus {existing_shift_data.docstatus}). Skipping update.",
                        #     "Shift Debug"
                        # )
                        continue
                    else:
                        next_shift_doc = frappe.get_doc("Station Shift Management", existing_shift_data.name)
                else:
                    # Create a new document (draft by default)
                    next_shift_doc = frappe.new_doc("Station Shift Management")
                    next_shift_doc.update({
                        "from_date": next_date,
                        "shift": next_shift,
                        "station": self.station,
                        "price_list": self.price_list,
                        "employee": employee,  # Set the employee for this shift
                    })

                # Process rows for this employee
                for row in rows:
                    # Check if there's already an entry for the employee and pump/tank in the next shift
                    existing_item = next(
                        (item for item in next_shift_doc.get("items") if item.pump_or_tank == row.pump_or_tank),
                        None
                    )

                    if existing_item:
                        # Update existing item's opening meter reading from the corresponding closing meter reading
                        opening_meter = frappe.db.get_value(
                            "Station Shift Management Item",  # Child table
                            {
                                "parent": self.name,
                                "pump_or_tank": row.pump_or_tank,
                                "employee_for_next_shift": row.employee_for_next_shift
                            },
                            "closing_meter_reading"
                        )
                        existing_item.opening_meter_reading = opening_meter
                    else:
                        # Map closing meter reading to opening meter reading for a new item row
                        next_shift_doc.append("items", {
                            "pump_or_tank": row.pump_or_tank,
                            "opening_meter_reading": row.closing_meter_reading,
                        })

                # Debug: Log the details of the next shift being created or updated
                # frappe.log_error(
                #     f"Processed next shift document for employee: {employee}, date: {next_date}",
                #     "Shift Debug"
                # )

                # Save or insert the shift document. They remain as drafts.
                if existing_shift_data:
                    next_shift_doc.save()
                else:
                    next_shift_doc.insert()

            frappe.msgprint(_("Next shifts created or updated successfully for all applicable employees."))

        except Exception as e:
            # Log the error and throw a generic error message
            frappe.log_error(frappe.get_traceback(), "Shift Creation Error")
            frappe.throw(_("An unexpected error occurred while creating the next shift."))
