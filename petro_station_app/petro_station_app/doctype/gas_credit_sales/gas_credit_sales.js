// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Gas Credit Sales", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Gas Credit Sales", {
	refresh(frm) {

	},

    date: function(frm) {
        // Calculate the due date as posting date + 30 days
        var postingDate = new Date(frm.doc.date);
        var dueDate = new Date(postingDate.setDate(postingDate.getDate() + 30));

        // Set the due date in the form
        frm.set_value('due_date', dueDate);
    },
    onload: function(frm) {
        frappe.call({
            method: 'petro_station_app.custom_api.api.get_filtered_doctype',
            callback: function(response) {
                if (response.message && response.message.length > 0) {
                    var filteredNames = response.message.map(item => item.name);
                    console.log(filteredNames);
                    
                    // Set query for the 'item' field in the 'expense_items' child table
                    frm.set_query('item', 'expense_items', function() {
                        return {
                            filters: {
                                name: ['in', filteredNames]
                            }
                        };
                    });
                    
                    // Set query for the 'party_type' field in the 'expense_items' child table
                    frm.set_query('party_type', 'expense_items', function() {
                        return {
                            filters: {
                                name: ['in', filteredNames]
                            }
                        };
                    });

                    // Refresh the 'expense_items' child table to apply the filters
                    frm.refresh_field('expense_items');
                }
            }
        });
    }
});

frappe.ui.form.on('Gas Sales Items', {
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

frappe.ui.form.on('Expense Claim Items', {
    amount: function (frm, cdt, cdn) {
        calculateTotalsTransfers(frm);
        
    }
});

function calculateTotalsTransfers(frm) {
    var total_qty = 0;
    frm.doc.expense_items.forEach(function (item) {
        total_qty += item.amount;
    });
    frm.set_value('grand_total', total_qty);
    refresh_field('expense_items');
}