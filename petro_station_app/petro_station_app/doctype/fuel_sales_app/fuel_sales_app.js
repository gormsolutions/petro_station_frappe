// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Fuel Sales App', {
//     after_submit: function(frm) {
//         // Refresh the page
//         location.reload();
//     }
// });
// Custom Script for Fuel Sales App
frappe.ui.form.on('Fuel Sales App', {
    
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Post Expense'), function() {
                frappe.call({
                    method: 'petro_station_app.custom_api.api.create_journal_entry',
                    args: {
                        docname: frm.doc.name,
                        employee:frm.doc.employee
                    },
                    callback: function(r) {
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
       
       fetch_attenant_pumps: function(frm) {
        fetchPumps(frm)
    },
    
    additional_discount_amount: function(frm) {
        calculate_and_validate_percentage_discount(frm);
    },
    net_total: function(frm) {
        calculate_and_validate_percentage_discount(frm);
    },
    create_reciept: function (frm) {
        create_customer_documents(frm);
        
        // postStockReconciliation(frm) 

    },

});


frappe.ui.form.on('Expense Claim Items', {
    amount: function (frm, cdt, cdn) {
        calculateTotalsTransfers(frm);
        
    }
});
frappe.ui.form.on('Fuel Sales Items', {
    item_code: function(frm, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        if (frm.doc.price_list) {
            frappe.model.set_value(cdt, cdn, 'price_list', frm.doc.price_list);
        }
    },
    closing: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];

        // Calculate qty based on amount and rate
        if (child_doc.rate) {
            var calculated_qty = (child_doc.closing - child_doc.opening); // Precision control
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }
    },
    opening: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];

        // Calculate qty based on amount and rate
        if (child_doc.rate) {
            var calculated_qty = (child_doc.closing - child_doc.opening); // Precision control
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
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

function calculate_percentage_discount(frm) {
    if (frm.doc.additional_discount_amount && frm.doc.net_total) {
        let percentage_discount = ((frm.doc.additional_discount_amount / frm.doc.net_total) * 100).toFixed(2);
        let cent = isNaN(percentage_discount) ? '0%' : percentage_discount + '%';
        frm.set_value('percentge_discount', cent);
    } else {
        frm.set_value('percentge_discount', '0%');
    }
}

function calculate_and_validate_percentage_discount(frm) {
    // Calculate percentage discount
    calculate_percentage_discount(frm);

    // Get percentage discount value
    let percentage_discount_value = parseFloat(frm.doc.percentge_discount);

    // Validate if percentage discount exceeds 10%
    if (percentage_discount_value > 10) {
        frappe.msgprint(__('Percentage Discount cannot exceed 10%.'));
        return;
    }

    // Save the form
    // frm.save()
    //     .then(() => {
    //         frappe.msgprint(__('Percentage Discount calculated and saved.'));
    //     })
    //     .catch(err => {
    //         frappe.msgprint(__('There was an error saving the document.'));
    //         console.error(err);
    //     });
}

frappe.ui.form.on('Fuel Customers Items', {
    qty: function (frm, cdt, cdn) {
        calculateCustomerTotals(frm);
    },
    rate: function (frm, cdt, cdn) {
        calculateCustomerTotals(frm);
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
                    fuel_sales_id: frm.doc.name
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
                new_grand_total += item.amount;  // Assuming amount contributes to grand_totals
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
            frappe.msgprint(__('The total of all Fuel Sales App ({0}) exceeds the Fuel Sales App grand total by {1}', 
                [combined_grand_totals, exceeded_amount]));
            return;  // Exit without creating any new documents
        }

        // If validation passes, proceed to create new Customer Documents
        for (let posting_date in grouped_items) {
            // Create a new Customer Document
            let custDoc = frappe.model.get_new_doc('Customer Document');
            custDoc.customer = frm.doc.customer;
            custDoc.pick_the_card = frm.doc.pick_the_card;
            custDoc.otp_code = frm.doc.otp_code;
            custDoc.customer_name = frm.doc.customer_name;
            custDoc.station = frm.doc.station;
            custDoc.price_list = frm.doc.price_list;
            custDoc.include_payments = frm.doc.include_payments;
            custDoc.date = posting_date;
            custDoc.time = frm.doc.time;
            custDoc.due_date = frm.doc.due_date;
            custDoc.net_total = 0;  // Will calculate below
            custDoc.total_qty = 0;  // Will calculate below
            custDoc.grand_totals = 0;  // Will calculate below
            custDoc.additional_discount_amount = frm.doc.additional_discount_amount;
            custDoc.fuel_sales_id = frm.doc.name;

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
                custDoc.grand_totals += item.amount;  // Assuming grand_totals is similar to net_total
            });

            // Save and submit the Customer Document
            frappe.db.insert(custDoc).then(doc => {
                // Submit the document after creation
                frappe.call({
                    method: "frappe.client.submit",
                    args: {
                        doc: doc
                    },
                    callback: function(response) {
                        frappe.msgprint(__('Customer Document {0} created and submitted', [response.message.name]));
                    }
                });
            }).catch(err => {
                frappe.msgprint(__('Failed to create Customer Document: {0}', [err.message]));
            });
        }
    }).catch(err => {
        frappe.msgprint(__('Error fetching existing Customer Documents: {0}', [err.message]));
    });
}

function fetchPumps(frm) {
    // Use a flag to track which pump_or_tank values have been processed
    let warehousesSet = new Set();

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

                // Iterate through the pump_or_tank values from the API response
                pumpOrTankValues.forEach(warehouse => {
                    // Check if the warehouse has already been processed
                    if (!warehousesSet.has(warehouse.pump_or_tank)) {
                        // Mark this warehouse as processed
                        warehousesSet.add(warehouse.pump_or_tank);

                        // Check if the 'items' table already has a row for this warehouse
                        let existingItem = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);
                        
                        if (!existingItem) {
                            // If no existing item, add a new row to 'items' table
                            let item = frm.add_child('items'); // Add a new row to items table
                            item.pos_profile = ''; // Set pos_profile initially as empty
                            item.price_list = ''; // Set price_list initially as empty
                            item.item_code = '';
                            item.meter_qtys = warehouse.qty_sold_on_meter_reading;
                            item.warehouse = warehouse.pump_or_tank; // Set the warehouse field to the value from API
                        } else {
                            // If the item exists, update the existing row
                            existingItem.meter_qtys = warehouse.qty_sold_on_meter_reading;
                        }

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
                                    // Update the POS Profile details if found
                                    let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);
                                    if (item) {
                                        item.pos_profile = posResponse.message.name; // Set POS Profile Name
                                        item.price_list = posResponse.message.selling_price_list; // Set the price list
                                        item.item_code = posResponse.message.custom_fuel;
                                    }

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
                                                let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);
                                                if (item) {
                                                    item.rate = priceResponse.message.price_list_rate;
                                                }
                                                // Refresh the table to reflect changes
                                                frm.refresh_field('items');
                                            }
                                        }
                                    });

                                    // Fetch total qty sold for this warehouse
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

                                            let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);
                                            if (item) {
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

                                                // Set item.qty with actual_qty
                                                item.qty = item.actual_qty;

                                                // Calculate item.amount as rate * qty
                                                item.amount = item.rate * item.qty;

                                                // Refresh the table to reflect changes
                                                frm.refresh_field('items');
                                            }
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

