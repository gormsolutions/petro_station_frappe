// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Customer Document", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Customer Document', {
    refresh: function (frm) {
    },
    before_load: function (frm) {
        // Set the from_date to the current date and time when creating a new document
        if (frm.is_new()) {
            let now = frappe.datetime.now_datetime();
            frm.set_value('posting_date', now);
        }
    },
    
    validate: function(frm) {
        if (frm.doc.has_fuel_card) {
            if (!frm.doc.card_number) {
                frappe.msgprint(__(`Please select the Valid Card Number for ${frm.doc.customer_name}.`));
                frappe.validated = false; // Prevent form submission
            }
        }
    },
    customer: function(frm) {
        // Clear the card field initially
        frm.set_value('pick_the_card', '');
    
        // Always hide the pick_the_card field initially
        frm.toggle_display('pick_the_card', false);
    
        // Get the selected customer
        var cust = frm.doc.customer;
    
        if (cust) {
            // Show loading indicator
            frm.set_df_property('pick_the_card', 'read_only', true); // Disable the field during loading
            frm.toggle_display('pick_the_card', false); // Hide the field
    
            // Call the server to get the list of cards
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Fuel Card',
                    filters: {
                        customer: cust,
                        docstatus: 1 // Filter only for submitted records
                    },
                    limit_page_length: 1 // Limit the results to 1 if you only need to check for existence
                },
                callback: function(response) {
                    // Hide loading indicator
                    console.log(response)
                    frm.set_df_property('pick_the_card', 'read_only', false); // Re-enable the field
    
                    if (response.message && response.message.length > 0) {
                        // If cards are found, set the query to filter the pick_the_card field
                        frm.set_query('pick_the_card', function() {
                            return {
                                filters: {
                                    customer: cust,
                                    docstatus: 1 // Ensure we only show submitted cards in the dropdown
                                }
                            };
                        });
    
                        // Show the pick_the_card field if cards exist
                        frm.toggle_display('pick_the_card', true);
                    } else {
                        // If no cards are found, clear the pick_the_card field
                        frm.set_value('pick_the_card', '');
                        
                        // Hide the pick_the_card field (it should already be hidden)
                        frm.toggle_display('pick_the_card', false);
                    }
                }
            });
        } else {
            // If no customer is selected, clear the pick_the_card field and hide it
            frm.set_value('pick_the_card', '');
            frm.toggle_display('pick_the_card', false);
        }
    },
    // station: function(frm) {
    //     frappe.call({
    //       method: 'petro_station_app.custom_api.api.fetch_details_cost_center',
    //       args: {
    //         station: frm.doc.station,
    //       },
    //       callback: function(r) {
    //         if (r.message) { // Check if the response contains a message
    //           var items = r.message.from_pos_profile; // Corrected key name
    //           var from_price_list = r.message.from_price_list; // Corrected key name
              
    //           if (from_price_list && Array.isArray(from_price_list) && from_price_list.length > 0) {
    //             frm.set_value('price_list', from_price_list[0].name);
    //           } else {
    //             console.log("No price lists data found in response.");
    //           }
    
    //           if (items && Array.isArray(items)) {
    //             // Clear existing items before populating (optional)
    //             frm.clear_table('items');
    
    //             // Loop through each item in the response
    //             for (var i = 0; i < items.length; i++) {
    //               var new_item = frm.add_child('items'); // Create a new child row
    
    //               // Set values from response to new item fields
    //               new_item.item_code = items[i].custom_fuel; // Replace with actual field names 
    //               new_item.pos_profile = items[i].name;
    //               new_item.warehouse = items[i].warehouse;
    //               new_item.rate = items[i].item_price;
    //               new_item.price_list = from_price_list[0].name;
    //               // ... Add other relevant fields
    //             }
    
    //             // Refresh the child table view after populating all items
    //             frm.refresh_field('items');
    //           } else {
    //             console.log("No items data found in response.");
    //           }
    //         }
    //       }
    //     });
    //   },
      card: function(frm) {
        // Fetch card details based on customer and card number
        if (frm.doc.customer && frm.doc.card) {
            fetchCardDetails(frm);
        } 
    },
    date: function(frm) {
        // Calculate the due date as posting date + 30 days
        var postingDate = new Date(frm.doc.date);
        var dueDate = new Date(postingDate.setDate(postingDate.getDate() + 30));

        // Set the due date in the form
        frm.set_value('due_date', dueDate);
    },
    grand_totals: function(frm) {
        calculateResult(frm);
    },
    additional_discount_amount: function(frm) {
        calculateResult(frm);
    }
    
    
    

});


frappe.ui.form.on('Fuel Sales Items', {
    qty: function (frm, cdt, cdn) {
        calculateTotals(frm);
    },
    rate: function (frm, cdt, cdn) {
        calculateTotals(frm);
    },
    item_code: function(frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];
        if (child_doc.item_code) {
            frappe.call({
                method: 'petro_station_app.custom_api.api.get_item_price_rate',
                args: {
                    item_code: child_doc.item_code,
                    price_list: frm.doc.price_list
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'rate', r.message);
                    }
                }
            });
        }
    }
});

// Function to fetch card details
function fetchCardDetails(frm) {
    if (frm.doc.pick_the_card && !frm.doc.has_fuel_card) { // Check if pick_the_card is set and has_fuel_card is not set
        frm.set_value('has_card', 1); // Set has_fuel_card to 1
        // frm.save_or_update(); // Save the form
    }
}

function calculateTotals(frm) {
    var total_qty = 0;
    var grand_total = 0;
    frm.doc.items.forEach(function (item) {
        total_qty += item.qty;
        item.amount = item.qty * item.rate;
        grand_total += item.amount;
    });
    frm.set_value('total_qty', total_qty);
    frm.set_value('grand_totals', grand_total);
    refresh_field('items');
}
function calculateResult(frm) {
    // Get the values of field1 and field2
    var field1Value = frm.doc.grand_totals;
    var field2Value = frm.doc.additional_discount_amount;

    // Perform the subtraction
    var result = field1Value - field2Value;

    // Update the result field
    frm.set_value('net_total', result);
}
