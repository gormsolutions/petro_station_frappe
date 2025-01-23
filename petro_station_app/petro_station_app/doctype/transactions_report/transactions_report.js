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
            // console.log(r)
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
            // console.log(r.message)
            if (r.message) {
                // console.log("Total Sales:", r.message.total_sales);
                console.log("Total Expenses:", r.message.total_expenses);
                frm.set_value('custom_station_expenses', r.message.total_expenses);
                frm.set_value('custom_prepaid', r.message.total_sales);
            }
        }
    });

    frappe.call({
        method: "petro_station_app.custom_api.transaction_report.stock_report.fetch_stock_entry_ledger_data", // Update with the actual path
        args: {
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            cost_center: frm.doc.station
        },
        callback: function (r) {
            if (r.message) {
                // console.log(r);
                const data_purchase_invoice = r.message['Purchase Invoice'];
                const data_sales_invoice = r.message['Sales Invoice'];
                const child_table_field = 'stock_report_items'; // Replace with your child table fieldname
                frm.clear_table(child_table_field);
    
                // Loop through the Purchase Invoice data and populate the child table
                data_purchase_invoice.forEach(purchase_entry => {
                    let child = frm.add_child(child_table_field);
    
                    // Populate child table with purchase entry data
                    frappe.model.set_value(child.doctype, child.name, {
                        qty_in: purchase_entry.qty_in || 0,  // Purchase quantity
                        buying_price: purchase_entry.buying_price || 0, // Purchase price
                        item: purchase_entry.item_code,
                        buying_amount: purchase_entry.total_buying_amount || 0, // Total buying amount
                        purchase_voucher_no: purchase_entry.voucher_no || ''
                    });
                });
    
                // Loop through the Sales Invoice data and populate the child table
                data_sales_invoice.forEach(sales_entry => {
                    let child = frm.add_child(child_table_field);
    
                    // Populate child table with sales entry data
                    frappe.model.set_value(child.doctype, child.name, {
                        qty_out: sales_entry.qty_out || 0,  // Sales quantity
                        selling_price: sales_entry.selling_price || 0, // Sales price
                        item: sales_entry.item_code,
                        selling_amount: sales_entry.total_selling_amount || 0, // Total selling amount
                        sales_voucher_no: sales_entry.voucher_no || ''
                    });
                });
    
                frm.refresh_field(child_table_field);
                frappe.msgprint(__('Stock entries have been fetched and populated.'));
            }
        }
    });
    
    
        
}





