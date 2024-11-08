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
