// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Transactional Report", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Transactional Report', {
    refresh(frm) {
        frm.add_custom_button(__('Fetch Stock Balances'), function () {

            if (!frm.doc.transaction_date) {
                frappe.msgprint(__('Please set Transaction Date first.'));
                return;
            }
            if (!frm.doc.gas_store || !frm.doc.empty_store) {
                frappe.msgprint(__('Please set Gas Store and Empty Store first.'));
                return;
            }

            // Clear child table once
            frm.clear_table('items');

            let mergedData = {}; // Keyed by item_code

            // First API: opening_qty
            frappe.call({
                method: 'petro_station_app.custom_api.gas_invoice.stock_balances.get_qty_as_of_date',
                args: { as_of_date: frm.doc.transaction_date },
                callback: function(r1) {
                    if (r1.message) {

                        function collect_opening(data, section) {
                            data.forEach(row => {
                                if (!mergedData[row.item_code]) mergedData[row.item_code] = {};
                                mergedData[row.item_code].item_in_stock = row.item_code;
                                mergedData[row.item_code].opening_qty = row.qty_after_transaction || 0;
                                mergedData[row.item_code].section_type = section;
                            });
                        }

                        collect_opening(r1.message.Gas[frm.doc.gas_store] || [], 'Gas');
                        collect_opening(r1.message.Empties[frm.doc.empty_store] || [], 'Empty');
                        collect_opening(r1.message.Extras[frm.doc.gas_store] || [], 'Extras');
                    }

                    // Second API: received, returned, sales
                    frappe.call({
                        method: 'petro_station_app.custom_api.gas_invoice.stock_balances.qty_as_of_date',
                        args: { as_of_date: frm.doc.transaction_date },
                        callback: function(r2) {
                            if (r2.message) {

                                function collect_qty(data, section) {
                                    data.forEach(row => {
                                       if (!mergedData[row.item_code]) mergedData[row.item_code] = { item_in_stock: row.item_code, section_type: section };

                                        mergedData[row.item_code].received = row.purchase_received || 0;
                                        mergedData[row.item_code].returned = Math.abs(row.purchase_returned || 0); // Always positive
                                        mergedData[row.item_code].sales = Math.abs(row.sales_qty || 0); // Always positive
                                    });
                                }

                                collect_qty(r2.message.Gas[frm.doc.gas_store] || [], 'Gas');
                                collect_qty(r2.message.Empties[frm.doc.empty_store] || [], 'Empty');
                                collect_qty(r2.message.Extras[frm.doc.gas_store] || [], 'Extras');

                                // Add merged rows to child table
                                Object.values(mergedData).forEach(row => {
                                    // Ensure all quantities are numbers
                                    row.opening_qty = row.opening_qty || 0;
                                    row.received = row.received || 0;
                                    row.returned = row.returned || 0;
                                    row.sales = row.sales || 0;

                                    // Calculate closing quantity
                                    row.closing_qty = (row.opening_qty + row.received) - (row.returned + row.sales);
                                    

                                    let child = frm.add_child('items');
                                    Object.assign(child, row);
                                });

                                frm.refresh_field('items');
                                frappe.msgprint(__('Child table populated successfully with merged data.'));
                            }
                        }
                    });

                }
            });

        });
    }
});
