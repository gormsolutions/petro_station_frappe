// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Customer Statement", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Customer Statement', {
    refresh: function(frm) {
        // Add a custom button to fetch statement details and apply discount
        frm.add_custom_button(__('Get Statement Details'), function() {
            get_statement_details(frm).then(() => {
                // Apply additional discount after fetching details
                apply_additional_discount(frm);
            });
        });
    }
});

function get_statement_details(frm) {
    frappe.call({
        method: 'petro_station_app.custom_api.statement.customer_statement.get_customers',
        args: {
            customer: frm.doc.customer,
            from_date: frm.doc.from_date,
            to_date: frm.doc.to_date,
            cost_center: frm.doc.cost_center
        },
        callback: function(r) {
            console.log(r);
            if (r.message) {
                let data = r.message.sales_invoice_data;

                // Calculate balance brought forward  
                let balance_brought_forward = r.message.balance_brought_forward || 0;
                let paid_amount = r.message.total_paid_amount || 0;
                let running_balance = balance_brought_forward;  // Start the running balance with the brought forward balance
                let bf = balance_brought_forward - paid_amount;
                frm.set_value('balance_forward', balance_brought_forward);

                // Clear existing child table data
                frm.clear_table('statement_details');

                // Add a row for balance brought forward at the top Balance Forward
                if (balance_brought_forward !== 0) {
                    let child = frm.add_child('statement_details');
                    frappe.model.set_value(child.doctype, child.name, 'opening', "OPENING BAL");
                    frappe.model.set_value(child.doctype, child.name, 'invoice_date', frm.doc.from_date); // Use the start date as the date
                    frappe.model.set_value(child.doctype, child.name, 'entry_type', 'Balance Brought Forward');  // Indicate type as Balance Brought Forward
                    frappe.model.set_value(child.doctype, child.name, 'running_balance', balance_brought_forward); // Set balance brought forward as the running balance
                }

                // Create a combined array with all entries (sales_invoice_data, payments, and gl_entries)
                let all_entries = [];

                // Add invoices
                data.forEach(function(invoice) {
                    all_entries.push({
                        type: 'Invoice',
                        item_code: invoice.item_code,
                        vehicle_no: invoice.custom_vehicle_plates,
                        qty: invoice.qty,
                        rate: invoice.rate,
                        amount: invoice.amount,
                        posting_date: invoice.posting_date, // Use posting_date for sorting
                        station_inv: invoice.cost_center,
                        invoice_vourcher: invoice.invoice_name,
                        credit_sales_id: invoice.credit_sales_id,
                        sales_app_id: invoice.cash_refund_id,
                        order_no: invoice.order_number,
                        invoice_no: invoice.invoice_no
                    });
                });

                // Add payments
                r.message.payments.forEach(function(payment) {
                    all_entries.push({
                        type: 'Payment',
                        paid_amount: payment.paid_amount,
                        posting_date: payment.posting_date, // Use posting_date for sorting
                        payment_entry: payment.payment_entry_name,
                        station_pe: payment.cost_center
                    });
                });

                // Add GL entries
                r.message.gl_entries.forEach(function(gl_entry) {
                    all_entries.push({
                        type: 'GL Entry',
                        amount: gl_entry.debit,
                        paid_amount: gl_entry.credit,
                        posting_date: gl_entry.posting_date, // Use posting_date for sorting
                        station_jl: gl_entry.cost_center,
                        voucher_no: gl_entry.voucher_no
                    });
                });

                // Sort all entries by posting_date (oldest to newest)
                all_entries.sort((a, b) => new Date(a.posting_date) - new Date(b.posting_date));

                // Add sorted entries to child table
                all_entries.forEach(function(entry) {
                    let child = frm.add_child('statement_details');

                    frappe.model.set_value(child.doctype, child.name, 'invoice_date', entry.posting_date);

                    if (entry.type === 'Invoice') {
                        frappe.model.set_value(child.doctype, child.name, 'item_code', entry.item_code);
                        frappe.model.set_value(child.doctype, child.name, 'vehicle_no', entry.vehicle_no);
                        frappe.model.set_value(child.doctype, child.name, 'qty', entry.qty);
                        frappe.model.set_value(child.doctype, child.name, 'rate', entry.rate);
                        frappe.model.set_value(child.doctype, child.name, 'amount', entry.amount);
                        frappe.model.set_value(child.doctype, child.name, 'station_inv', entry.station_inv);
                        frappe.model.set_value(child.doctype, child.name, 'invoice_vourcher', entry.invoice_vourcher);
                        frappe.model.set_value(child.doctype, child.name, 'credit_sales_id', entry.credit_sales_id);
                        frappe.model.set_value(child.doctype, child.name, 'sales_app_id', entry.sales_app_id);
                        frappe.model.set_value(child.doctype, child.name, 'order_no', entry.order_no);
                        frappe.model.set_value(child.doctype, child.name, 'invoice_no', entry.invoice_no);
                        frappe.model.set_value(child.doctype, child.name, 'entry_type', 'Invoice');
                        running_balance += entry.amount;
                    } else if (entry.type === 'Payment') {
                        frappe.model.set_value(child.doctype, child.name, 'paid_amount', entry.paid_amount);
                        frappe.model.set_value(child.doctype, child.name, 'payment_entry', entry.payment_entry);
                        frappe.model.set_value(child.doctype, child.name, 'station_pe', entry.station_pe);
                        frappe.model.set_value(child.doctype, child.name, 'entry_type', 'Payment');
                        running_balance -= entry.paid_amount;
                    } else if (entry.type === 'GL Entry') {
                        frappe.model.set_value(child.doctype, child.name, 'amount', entry.amount);
                        frappe.model.set_value(child.doctype, child.name, 'paid_amount', entry.paid_amount);
                        frappe.model.set_value(child.doctype, child.name, 'station_jl', entry.station_jl);
                        frappe.model.set_value(child.doctype, child.name, 'voucher_no', entry.voucher_no);
                        frappe.model.set_value(child.doctype, child.name, 'entry_type', 'GL Entry');
                        running_balance += entry.amount;
                        running_balance -= entry.paid_amount;
                    }

                    frappe.model.set_value(child.doctype, child.name, 'running_balance', running_balance); // Update running balance
                });

                // Refresh the field to display the updated child table
                frm.refresh_field('statement_details');

                // Recalculate totals after populating the child table
                calculateTotals(frm);
            }
        }
    });
}


function calculateTotals(frm) {
    var total_amount = 0;
    var total_paid = 0;
    frm.doc.statement_details.forEach(function(item) {
        total_amount += item.amount || 0;  // Add amount, default to 0 if undefined
        total_paid += item.paid_amount || 0;  // Add paid amount, default to 0 if undefined
    });
    var bf = frm.doc.balance_forward
    var total_outford = (bf - total_paid) + total_amount
    var outstanding_amount = total_amount - total_paid;
     
    frm.set_value('total_invoices', total_amount);  // Set total invoices
    frm.set_value('total_paid', total_paid);  // Set total paid
    frm.set_value('total_outstanding_amount', total_outford);  // Set total outstanding amount
    

    // Refresh the parent fields
    frm.refresh_field('total_invoices');
    frm.refresh_field('total_paid');
    frm.refresh_field('total_outstanding_amount');
}

function additionDiscount(frm) {
    let total_additional_discount = 0;
    let total_outstanding_amount = 0;
    let need_to_save = false;

    // Fetch linked statement details
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Invoice Table Statement',
            filters: { parent: frm.doc.name }, // Fetch linked statement details
            fields: ['name', 'invoice_vourcher', 'additional_discount_amount', 'outstanding_amount'] // Fetch outstanding_amount
        },
        callback: function(response) {
            const statement_details = response.message || [];
            let processed_count = 0;

            if (statement_details.length > 0) {
                statement_details.forEach((detail) => {
                    // Accumulate additional discount from 'Statement Details'
                    total_additional_discount += detail.additional_discount_amount || 0;
                    
                    // Accumulate total outstanding amount
                    total_outstanding_amount += detail.outstanding_amount || 0;

                    if (detail.invoice_vourcher) {
                        // Fetch the linked Sales Invoice to ensure correct discount
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'Sales Invoice',
                                name: detail.invoice_vourcher
                            },
                            callback: function(sales_invoice) {
                                const discount_amount = sales_invoice.message.discount_amount || 0;

                                // Update additional_discount_amount if necessary
                                if (!detail.additional_discount_amount || detail.additional_discount_amount !== discount_amount) {
                                    frappe.model.set_value('Statement Details', detail.name, 'additional_discount_amount', discount_amount);
                                    need_to_save = true; // Mark for saving
                                }

                                // Ensure all records are processed
                                processed_count++;
                                if (processed_count === statement_details.length) {
                                    finalizeStatement(frm, total_additional_discount, total_outstanding_amount, need_to_save);
                                }
                            }
                        });
                    } else {
                        processed_count++;
                        // Finalize when all records are processed
                        if (processed_count === statement_details.length) {
                            finalizeStatement(frm, total_additional_discount, total_outstanding_amount, need_to_save);
                        }
                    }
                });
            }
        }
    });
}

// Function to finalize and update the Statement
function finalizeStatement(frm, total_additional_discount, total_outstanding_amount, need_to_save) {
    // Set the total additional discount
    frm.set_value('additional_discount_amount', total_additional_discount);

    // Set the total outstanding amount
    frm.set_value('total_outstanding_amount', total_outstanding_amount);

    // Save the document if any updates were made
    if (need_to_save) {
        frm.save();
    }
}

