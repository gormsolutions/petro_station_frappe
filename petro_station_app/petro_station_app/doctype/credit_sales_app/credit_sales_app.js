// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Credit Sales App", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Credit Sales App', {
   refresh: function (frm) {

    if (frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
        updateActualQtyOnly(frm);
    }

        // Populate Fuel Customers Items if needed
        populateFuelCustomersItems(frm);
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Post Expense'), function () {
                frappe.call({
                    method: 'petro_station_app.custom_api.api.create_journal_entry_cr',
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            frappe.msgprint(__('Journal Entry created successfully'));
                            // frm.set_value('je_id', r.message);
                            // frm.save_or_update();
                        }
                    }
                });
            });

        }
    },
    before_load: function (frm) {
        // Set the from_date to the current date and time when creating a new document
        if (frm.is_new()) {
            let now = frappe.datetime.now_datetime();
            frm.set_value('date', now);
        }
    },

    shift: function (frm) {
        fetchPumps(frm)
    },
    employee: function (frm) {
        fetchPumps(frm)
    },
    date: function (frm) {
        fetchPumps(frm)
    },

    validate: function (frm) {
        if (frm.doc.has_fuel_card) {
            if (!frm.doc.card_number) {
                frappe.msgprint(__(`Please select the Valid Card Number for ${frm.doc.customer_name}.`));
                frappe.validated = false; // Prevent form submission
            }
        }
        // validate_previous_day_shifts(frm);

    },
    before_submit: function(frm) {
        // Calling the function on submission
        validate_previous_day_shifts(frm);
    },
    customer: function (frm) {
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
                callback: function (response) {
                    // Hide loading indicator
                    frm.set_df_property('pick_the_card', 'read_only', false); // Re-enable the field

                    if (response.message && response.message.length > 0) {
                        // If cards are found, set the query to filter the pick_the_card field
                        frm.set_query('pick_the_card', function () {
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
    create_reciept: function (frm) {
        create_customer_documents(frm);

        // postStockReconciliation(frm) 

    },
    // before_submit: function (frm) {
    //     create_customer_documents(frm);

    // }


});

frappe.ui.form.on('Expense Claim Items', {
    amount: function (frm, cdt, cdn) {
        calculateTotalsTransfers(frm);
    }
});
frappe.ui.form.on('Fuel Sales Items', {
    item_code: function (frm, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        if (frm.doc.price_list) {
            frappe.model.set_value(cdt, cdn, 'price_list', frm.doc.price_list);
        }
    },
    amount: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];

        // Calculate qty based on amount and rate
        if (child_doc.amount && child_doc.rate) {
            var calculated_qty = (child_doc.amount / child_doc.rate); // Precision control
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }
    },
});


function calculateTotalsTransfers(frm) {
    var total_qty = 0;
    frm.doc.expense_items.forEach(function (item) {
        total_qty += item.amount;
    });
    frm.set_value('grand_total', total_qty);
    refresh_field('expense_items');
}

frappe.ui.form.on('Fuel Customers Items', {
    qty: function (frm, cdt, cdn) {
        calculateCustomerTotals(frm);
    },
    rate: function (frm, cdt, cdn) {
        calculateCustomerTotals(frm);
    },
    amount: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];

        // Calculate qty based on amount and rate
        if (child_doc.amount && child_doc.rate) {
            var calculated_qty = child_doc.amount / child_doc.rate;
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }

        calculateCustomerTotals(frm);
    },
    item_code: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];
        if (child_doc.item_code) {
            frappe.call({
                method: 'petro_station_app.custom_api.api.get_item_price_rate',
                args: {
                    item_code: child_doc.item_code,
                    price_list: frm.doc.price_list
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'rate', r.message);
                    }
                }
            });
        }
    }
});


function calculateCustomerTotals(frm) {
    var total_qty = 0;
    var grand_total = 0;
    frm.doc.fuel_items.forEach(function (item) {
        total_qty += item.qty;
        item.amount = item.qty * item.rate;
        grand_total += item.amount;
    });
    frm.set_value('total_items_qty', total_qty);
    frm.set_value('grand_items_total', grand_total);
    refresh_field('fuel_items');
}

function create_customer_documents(frm) {
    // Function to calculate the grand total from existing Customer Documents
    const get_total_existing_grand_totals = () => {
        return new Promise((resolve, reject) => {
            frappe.db.get_list('Customer Document', {
                filters: {
                    credit_sales_id: frm.doc.name
                },
                fields: ['grand_totals']
            }).then(records => {
                let existing_grand_total = 0;
                records.forEach(doc => {
                    existing_grand_total += doc.grand_totals;
                });
                resolve(existing_grand_total);
            }).catch(err => {
                reject(err);
            });
        });
    };

    // Calculate total grand total for the new customer documents to be created
    const get_new_grand_totals = (grouped_items) => {
        let new_grand_total = 0;
        for (let posting_date in grouped_items) {
            grouped_items[posting_date].forEach(item => {
                new_grand_total += item.amount; // Assuming amount contributes to grand_totals
            });
        }
        return new_grand_total;
    };

    // Group items by posting_date
    let grouped_items = {};
    frm.doc.fuel_items.forEach(item => {
        if (!grouped_items[item.posting_date]) {
            grouped_items[item.posting_date] = [];
        }
        grouped_items[item.posting_date].push(item);
    });

    // Get the total of the new grand totals
    let new_grand_totals = get_new_grand_totals(grouped_items);

    // Fetch the existing grand totals from the Customer Documents
    get_total_existing_grand_totals().then(existing_grand_totals => {
        // Calculate the combined grand totals (existing + new)
        let combined_grand_totals = existing_grand_totals + new_grand_totals;

        // Check if the combined grand totals exceed the Credit Sales App grand totals
        if (combined_grand_totals > frm.doc.grand_totals) {
            let exceeded_amount = combined_grand_totals - frm.doc.grand_totals;
            frappe.msgprint(__('The total of all Cash Refund ({0}) exceeds the Cash Refund grand total by {1}',
                [combined_grand_totals.toFixed(1), exceeded_amount.toFixed(1)]));
            return;
        } else if (combined_grand_totals < frm.doc.grand_totals) {
            let exceeded_amount = combined_grand_totals - frm.doc.grand_totals;
            frappe.msgprint(__('The total of all Cash Refund ({0}) is less than the Cash Refund grand total by {1}',
                [combined_grand_totals.toFixed(1), exceeded_amount.toFixed(1)]));

            // Proceed with the function only if the exceeded amount is -0.0
            if (exceeded_amount.toFixed(1) === '-0.0') {
                // Proceed with creating new Customer Documents
                create_new_customer_documents(grouped_items, frm);
            }
            return;
        }

        // If validation passes, proceed to create new Customer Documents
        create_new_customer_documents(grouped_items, frm);

    }).catch(err => {
        frappe.msgprint(__('Error fetching existing Customer Documents: {0}', [err.message]));
    });
}

// Function to create new Customer Documents
function create_new_customer_documents(grouped_items, frm) {
    for (let posting_date in grouped_items) {
        let invoice_no = grouped_items[posting_date][0].invoice_no; // Fetching invoice_no from the first item
        // Create a new Customer Document
        let custDoc = frappe.model.get_new_doc('Customer Document');
        custDoc.customer = frm.doc.customer;
        custDoc.pick_the_card = frm.doc.pick_the_card;
        custDoc.otp_code = frm.doc.otp_code;
        custDoc.customer_name = frm.doc.customer_name;
        custDoc.station = frm.doc.station;
        custDoc.price_list = frm.doc.price_list;
        custDoc.invoice_no = invoice_no;
        custDoc.include_payments = frm.doc.include_payments;
        custDoc.posting_date = posting_date;
        custDoc.time = frm.doc.time;
        custDoc.due_date = frm.doc.due_date;
        custDoc.net_total = 0; // Will calculate below
        custDoc.total_qty = 0; // Will calculate below
        custDoc.grand_totals = 0; // Will calculate below
        custDoc.additional_discount_amount = frm.doc.additional_discount_amount;
        custDoc.credit_sales_id = frm.doc.name;

        // Add fuel items to the new customer document and calculate totals
        grouped_items[posting_date].forEach(item => {
            let fuel_item = frappe.model.add_child(custDoc, 'Fuel Sales Items', 'items');
            fuel_item.price_list = item.price_list;
            fuel_item.pos_profile = item.pos_profile;
            fuel_item.item_code = item.item_code;
            fuel_item.qty = item.qty;
            fuel_item.rate = item.rate;
            fuel_item.amount = item.amount;
            fuel_item.warehouse = item.warehouse;
            fuel_item.uom = item.uom;
            fuel_item.order_number = item.order_number;
            fuel_item.milage = item.milage;
            fuel_item.number_plate = item.number_plate;

            // Update totals
            custDoc.net_total += item.amount;
            custDoc.total_qty += item.qty;
            custDoc.grand_totals += item.amount; // Assuming grand_totals is similar to net_total
        });

        // Save and submit the Customer Document
        frappe.db.insert(custDoc).then(doc => {
            // Submit the document after creation
            frappe.call({
                method: "frappe.client.submit",
                args: {
                    doc: doc
                },
                callback: function (response) {
                    frappe.msgprint(__('Customer Document {0} created and submitted', [response.message.name]));
                }
            });
        }).catch(err => {
            frappe.msgprint(__('Failed to create Customer Document: {0}', [err.message]));
        });
    }
}


// Function to create new Customer Documents
function create_new_customer_documents(grouped_items, frm) {
    for (let posting_date in grouped_items) {
        let invoice_no = grouped_items[posting_date][0].invoice_no; // Fetching invoice_no from the first item
        // Create a new Customer Document
        let custDoc = frappe.model.get_new_doc('Customer Document');
        custDoc.customer = frm.doc.customer;
        custDoc.pick_the_card = frm.doc.pick_the_card;
        custDoc.otp_code = frm.doc.otp_code;
        custDoc.customer_name = frm.doc.customer_name;
        custDoc.station = frm.doc.station;
        custDoc.price_list = frm.doc.price_list;
        custDoc.invoice_no = invoice_no;
        custDoc.include_payments = frm.doc.include_payments;
        custDoc.posting_date = posting_date;
        custDoc.time = frm.doc.time;
        custDoc.due_date = frm.doc.due_date;
        custDoc.net_total = 0; // Will calculate below
        custDoc.total_qty = 0; // Will calculate below
        custDoc.grand_totals = 0; // Will calculate below
        custDoc.additional_discount_amount = frm.doc.additional_discount_amount;
        custDoc.credit_sales_id = frm.doc.name;

        // Add fuel items to the new customer document and calculate totals
        grouped_items[posting_date].forEach(item => {
            let fuel_item = frappe.model.add_child(custDoc, 'Fuel Sales Items', 'items');
            fuel_item.price_list = item.price_list;
            fuel_item.pos_profile = item.pos_profile;
            fuel_item.item_code = item.item_code;
            fuel_item.qty = item.qty;
            fuel_item.rate = item.rate;
            fuel_item.amount = item.amount;
            fuel_item.warehouse = item.warehouse;
            fuel_item.uom = item.uom;
            fuel_item.order_number = item.order_number;
            fuel_item.milage = item.milage;
            fuel_item.number_plate = item.number_plate;

            // Update totals
            custDoc.net_total += item.amount;
            custDoc.total_qty += item.qty;
            custDoc.grand_totals += item.amount; // Assuming grand_totals is similar to net_total
        });

        // Save and submit the Customer Document
        frappe.db.insert(custDoc).then(doc => {
            // Submit the document after creation
            frappe.call({
                method: "frappe.client.submit",
                args: {
                    doc: doc
                },
                callback: function (response) {
                    frappe.msgprint(__('Customer Document {0} created and submitted', [response.message.name]));
                }
            });
        }).catch(err => {
            frappe.msgprint(__('Failed to create Customer Document: {0}', [err.message]));
        });
    }
}

function populateFuelCustomersItems(frm) {
    // console.log(frm.doc.items)
    // Check if there are no entries in the Fuel Customers Items table
    if (!frm.doc.fuel_items || frm.doc.fuel_items.length === 0) {
        // Ensure fuel_sales_items is defined
        if (frm.doc.items && frm.doc.items.length > 0) {
            frm.doc.items.forEach(function (item) {

                // Create a new item entry for Fuel Customers Items 
                let fuel_item = frm.add_child('fuel_items');
                fuel_item.price_list = item.price_list;
                fuel_item.pos_profile = item.pos_profile;
                fuel_item.item_code = item.item_code;
                fuel_item.qty = item.qty;
                fuel_item.rate = item.rate;
                fuel_item.amount = item.amount;
                fuel_item.posting_date = frm.doc.date;
                fuel_item.invoice_no = frm.doc.invoice_no;
                fuel_item.warehouse = item.warehouse;
                fuel_item.uom = item.uom;
                fuel_item.order_number = item.order_number;
                fuel_item.milage = item.milage;
                fuel_item.number_plate = item.number_plate;
            });
            frm.set_value('grand_items_total', frm.doc.grand_totals);
            frm.set_value('total_items_qty', frm.doc.total_qty);
            // Refresh the child table to show new entries
            frm.refresh_field('fuel_items');
        } else {
            console.error("No items found in Fuel Sales Items.");
        }
    }
}

function fetchPumps(frm) {
    // Clear the items table
    frm.doc.items = [];
    frm.refresh_field('items'); // Refresh the table to reflect changes

    // Call to the backend to fetch pump_or_tank values
    frappe.call({
        method: 'petro_station_app.custom_api.fetch_pumps.fetch_pumps.get_pump_or_tank', // Your API method
        args: {
            'date': frm.doc.date,
            'employee': frm.doc.employee,
            'shift': frm.doc.shift,
            'station': frm.doc.station
        },
        callback: function (response) {
            if (response.message && response.message.length > 0) {
                // response.message contains an array of pump_or_tank values
                let pumpOrTankValues = response.message; // Array of pump_or_tank values

                // Use a flag to track whether the warehouse has been set already
                let warehousesSet = new Set();

                // Iterate through the pump_or_tank values from the API response
                pumpOrTankValues.forEach(warehouse => {
                    // Check if the warehouse has already been processed
                    if (!warehousesSet.has(warehouse.pump_or_tank)) {
                        // Mark this warehouse as processed
                        warehousesSet.add(warehouse.pump_or_tank);

                        // Fetch the POS Profile for the current warehouse (pump_or_tank value)
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'POS Profile',
                                filters: {
                                    warehouse: warehouse.pump_or_tank // Filter by warehouse to get the POS Profile
                                }
                            },
                            callback: function (posResponse) {
                                if (posResponse.message) {
                                    // Add items to the 'items' child table and set values once for the warehouse
                                    let item = frm.add_child('items'); // Add a new row to items table
                                    // Set pos_profile, price_list, and warehouse fields in the item
                                    item.pos_profile = posResponse.message.name; // Set POS Profile Name
                                    item.price_list = posResponse.message.selling_price_list; // Set the price list
                                    item.item_code = posResponse.message.custom_fuel;
                                    item.meter_qtys = warehouse.qty_sold_on_meter_reading;
                                    item.warehouse = warehouse.pump_or_tank; // Set the warehouse field to the value from API

                                    // Fetch the item price from the 'Item Price' doctype
                                    frappe.call({
                                        method: 'frappe.client.get',
                                        args: {
                                            doctype: 'Item Price',
                                            filters: {
                                                item_code: item.item_code,
                                                price_list: frm.doc.price_list
                                            },
                                            fieldname: 'price_list_rate' // Get the price from the price list
                                        },
                                        callback: function (priceResponse) {
                                            if (priceResponse.message) {
                                                // Set the price (rate) fetched from the Item Price
                                                item.rate = priceResponse.message.price_list_rate;

                                                // Refresh the table to reflect changes
                                                frm.refresh_field('items');
                                            }
                                        }
                                    });

                                    frappe.call({
                                        method: 'petro_station_app.custom_api.fetch_pumps.fetch_pumps.get_total_qty',
                                        args: {
                                            'from_date': frm.doc.date,
                                            'employee': frm.doc.employee,
                                            'shift': frm.doc.shift,
                                            'station': frm.doc.station,
                                            'pump_or_tank_list': JSON.stringify([warehouse.pump_or_tank])
                                        },
                                        callback: function (qtyResponse) {
                                            console.log('qtyResponse.message:', qtyResponse.message);
                                            // Convert the qtyResponse.message to a number and set the quantity
                                            let qtySold = Number(qtyResponse.message);
                                            
                                            // Set the total quantity and calculate actual quantity
                                            item.qty_sold = qtySold;

                                            // If qtySold is 0 or falsy, set actual_qty to qty_sold_on_meter_reading
                                            if (!qtySold) { // Handles 0, null, undefined, or other falsy values
                                                console.log('Setting actual_qty to:', warehouse.qty_sold_on_meter_reading);
                                                item.actual_qty = warehouse.qty_sold_on_meter_reading; // Set when qty is falsy
                                            } else {
                                                console.log('Calculating actual_qty with deduction');
                                                item.actual_qty = warehouse.qty_sold_on_meter_reading - qtySold;
                                            }

                                            // Refresh the table to reflect changes
                                            frm.refresh_field('items');
                                        }
                                    });
                                }
                            }
                        });
                    }
                });
            } else {
                // If no response or empty response
                frappe.msgprint(__('No pump or tank locations found for the selected criteria.'));
            }
        }
    });
}

function updateActualQtyOnly(frm) {
    frm.doc.items.forEach(item => {
        if (item.warehouse && item.meter_qtys) {
            frappe.call({
                method: 'petro_station_app.custom_api.fetch_pumps.fetch_pumps.get_total_qty',
                args: {
                    'from_date': frm.doc.date,
                    'employee': frm.doc.employee,
                    'shift': frm.doc.shift,
                    'station': frm.doc.station,
                    'pump_or_tank_list': JSON.stringify([item.warehouse])
                },
                callback: function (qtyResponse) {
                    let qtySold = Number(qtyResponse.message);
                    item.qty_sold = qtySold;

                    if (!qtySold) {
                        item.actual_qty = item.meter_qtys;
                    } else {
                        item.actual_qty = item.meter_qtys - qtySold;
                    }

                    frm.refresh_field('items');
                }
            });
        }
    });
}



function validate_previous_day_shifts(frm) {
    frappe.call({
        method: 'petro_station_app.custom_api.Create_shifts.create_shift.validate_previous_day_shifts',
        args: {
            station: frm.doc.station,
            posting_date: frm.doc.date
        },
        callback: function(r) {
            // console.log('Response from server:', r);

            if (r.message) {
                if (!r.message.status) {
                    // Display the validation message with HTML rendered properly
                    frappe.msgprint({
                        title: __('Previous Day\'s Closure Validation'),
                        indicator: 'red',
                        message: r.message.message,
                        unsafe: true  // Allow HTML to be rendered in the message
                    });
                    frappe.validated = false;  // Block the save action
                } else {
                    // If validation passes, display a success message
                    // frappe.msgprint({
                    //     title: __('Validation Passed'),
                    //     indicator: 'green',
                    //     message: __('All pumps are correctly submitted.')
                    // });
                    frappe.validated = true;  // Allow save action
                }
            }
        },
        error: function(err) {
            // Handle errors during the server call
            frappe.msgprint({
                title: __('Validation Error'),
                indicator: 'red',
                message: err.message || __('An error occurred while validating shifts.')
            });
            frappe.validated = false;  // Stop the save action
        }
    });
}






