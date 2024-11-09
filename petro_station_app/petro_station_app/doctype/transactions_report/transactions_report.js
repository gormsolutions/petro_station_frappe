// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Transactions Report", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Transactions Report', {
    refresh: function(frm) {
        // Add a button to trigger the population of the statement details
        frm.add_custom_button(__('Get Report Details'), function() {
            // First, get statement details
            get_statement_details(frm)
        });
    }
});


function get_statement_details(frm) {
    frappe.call({
        method: 'petro_station_app.custom_api.statement.transaction_report.get_transaction_report_gl',
        args: {
            transaction_id: frm.doc.transaction_id,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            station: frm.doc.station
        },
        callback: function(r) {
            console.log(r);
            if (r.message) {
                let data = r.message;
                let grand_totals = 0;
                frm.clear_table('transaction_report_accounts');
                data.forEach(function(item) {
                    let child = frm.add_child('transaction_report_accounts');
                    frappe.model.set_value(child.doctype, child.name, 'account', item.account);
                    frappe.model.set_value(child.doctype, child.name, 'amount', item.balance);
                    grand_totals += item.balance;
                });
                frm.set_value('grand_totals', grand_totals);
                frm.refresh_field('transaction_report_accounts');
            }
       }
    });
}


