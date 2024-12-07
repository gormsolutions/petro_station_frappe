// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Transactions Report", {
// 	refresh(frm) {

// 	},
// });

// frappe.ui.form.on('Transactions Report', {
//     refresh: function(frm) {
//         // Add a button to trigger the population of the statement details
//         frm.add_custom_button(__('Get Report Details'), function() {
//             // First, get statement details
//             get_statement_details(frm)
//         });
//     }
// });


// function get_statement_details(frm) {
//     frappe.call({
//         method: 'petro_station_app.custom_api.statement.transaction_report.get_transaction_report_gl',
//         args: {
//             transaction_id: frm.doc.transaction_id,
//             from_date: frm.doc.from_date,
//             to_date: frm.doc.to_date,
//             station: frm.doc.station
//         },
//         callback: function(r) {
//             console.log(r);
//             if (r.message) {
//                 let data = r.message;
//                 let grand_totals = 0;
//                 frm.clear_table('transaction_report_accounts');
//                 data.forEach(function(item) {
//                     let child = frm.add_child('transaction_report_accounts');
//                     frappe.model.set_value(child.doctype, child.name, 'account', item.account);
//                     frappe.model.set_value(child.doctype, child.name, 'amount', item.balance);
//                     grand_totals += item.balance;
//                 });
//                 frm.set_value('grand_totals', grand_totals);
//                 frm.refresh_field('transaction_report_accounts');
//             }
//        }
//     });
// }

frappe.ui.form.on('Transactions Report', {
    refresh: function(frm) {
        // Add a button to trigger the population of the statement details
        frm.add_custom_button(__('Get Report Details'), function() {
            // First, get statement details
            get_statement_details(frm);
        });
    }
});

function get_statement_details(frm) {
    // Fetch data excluding VIVO
    frappe.call({
        method: 'petro_station_app.custom_api.statement.transaction_report.get_transaction_report_gl_withoutvivo',
        args: {
            transaction_id: frm.doc.transaction_id,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            station: frm.doc.station
        },
        callback: function (r) {
            if (r.message) {
                let data = r.message;
                let grand_totals = 0;
                let account_type_totals = {};

                // Clear both tables
                frm.clear_table('transaction_report_accounts');
                frm.clear_table('account_type_items');

                // Process account types and populate child tables
                data.forEach(function (item) {
                    // Add data to the transaction_report_accounts table
                    let child = frm.add_child('transaction_report_accounts');
                    frappe.model.set_value(child.doctype, child.name, 'account', item.account);
                    frappe.model.set_value(child.doctype, child.name, 'amount', item.balance);
                    grand_totals += item.balance;

                    // Process account type for totals
                    frappe.db.get_value('Account', { name: item.account }, 'account_type')
                        .then(res => {
                            let account_type = res.message.account_type;
                            if (account_type) {
                                if (!account_type_totals[account_type]) {
                                    account_type_totals[account_type] = 0;
                                }
                                account_type_totals[account_type] += item.balance;

                                // Populate account_type_items table dynamically
                                frm.clear_table('account_type_items'); // Clear to avoid duplicates
                                Object.keys(account_type_totals).forEach(function (type) {
                                    let accountTypeChild = frm.add_child('account_type_items');
                                    accountTypeChild.account_type = type;
                                    accountTypeChild.amount = account_type_totals[type];
                                });
                                frm.refresh_field('account_type_items');
                            }
                        });
                });

                // Set and refresh the grand total field
                frm.set_value('grand_totals', grand_totals);
                frm.refresh_field('transaction_report_accounts');
            }
        }
    });

    // Fetch data including VIVO
    frappe.call({
        method: 'petro_station_app.custom_api.statement.transaction_report.get_transaction_report_gl_withvivo',
        args: {
            transaction_id: frm.doc.transaction_id,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            station: frm.doc.station
        },
        callback: function (r) {
            if (r.message) {
                let data = r.message; // Ensure correct data object
                if (data.length > 0) {
                    let vivoBalance = data[0]?.balance || 0; // Safely access balance field
                    frm.set_value('vivo_card', vivoBalance);
                }
            }
        }
    });

    //  Fetch total sales from Sales Invoices
    frappe.call({
        method: 'petro_station_app.custom_api.statement.transaction_report.get_daily_totals',
        args: {
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            cost_center: frm.doc.station
        },
        callback: function(r) {
            if (r.message) {
                console.log("Total Sales:", r.message.total_sales);
                console.log("Total Expenses:", r.message.total_expenses);
                frm.set_value('custom_station_expenses', r.message.total_expenses);
                frm.set_value('custom_prepaid', r.message.total_sales);
            }
        }
    });
    
        
}



