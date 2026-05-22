// Copyright (c) 2024, mututa paul and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fuel Sales App', {

    before_submit: function (frm) {
        validate_previous_day_shifts(frm);
    },

    refresh: function (frm) {

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Post Expense'), function () {
                frappe.call({
                    method: 'petro_station_app.custom_api.api.create_journal_entry',
                    args: {
                        docname: frm.doc.name,
                        employee: frm.doc.employee
                    },
                    callback: function (r) {
                        if (!r.exc && r.message) {
                            frappe.msgprint(__('Journal Entry created successfully'));
                        }
                    }
                });
            });
        }



    
    
    },

    

    fetch_attenant_pumps: function (frm) {
        fetchPumps(frm);
    },

    additional_discount_amount: function (frm) {
        calculate_and_validate_percentage_discount(frm);
    },

    net_total: function (frm) {
        calculate_and_validate_percentage_discount(frm);
    },

    create_reciept: function (frm) {
        create_customer_documents(frm);
    }

});


// =========================
// VALIDATION (SAFE WRAP ONLY)
// =========================
function validate_previous_day_shifts(frm) {
    frappe.call({
        method: 'petro_station_app.custom_api.Create_shifts.create_shift.validate_previous_day_shifts',
        args: {
            station: frm.doc.station,
            posting_date: frm.doc.date
        },
        callback: function (r) {
            if (r.message && !r.message.status) {
                frappe.msgprint(r.message.message);
                frappe.validated = false;
            }
        },
        error: function (err) {
            frappe.msgprint({
                title: __('Validation Error'),
                indicator: 'red',
                message: err.message || __('An error occurred while validating shifts.')
            });
            frappe.validated = false;
        }
    });
}


// =========================
// EXPENSE ITEMS
// =========================
frappe.ui.form.on('Expense Claim Items', {
    amount: function (frm) {
        calculateTotalsTransfers(frm);
    }
});

function calculateTotalsTransfers(frm) {
    var total_qty = 0;

    (frm.doc.expense_items || []).forEach(function (item) {
        total_qty += item.amount;
    });

    frm.set_value('grand_total', total_qty);
    refresh_field('expense_items');
}


// =========================
// FUEL SALES ITEMS CHILD TABLE
// =========================
frappe.ui.form.on('Fuel Sales Items', {

    item_code: function (frm, cdt, cdn) {
        var item = frappe.get_doc(cdt, cdn);
        if (frm.doc.price_list) {
            frappe.model.set_value(cdt, cdn, 'price_list', frm.doc.price_list);
        }
    },

    closing: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];
        if (child_doc.rate) {
            var calculated_qty = (child_doc.closing - child_doc.opening);
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }
    },

    opening: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];
        if (child_doc.rate) {
            var calculated_qty = (child_doc.closing - child_doc.opening);
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }
    },

    amount: function (frm, cdt, cdn) {
        var child_doc = locals[cdt][cdn];
        if (child_doc.amount && child_doc.rate) {
            var calculated_qty = (child_doc.amount / child_doc.rate);
            frappe.model.set_value(cdt, cdn, 'qty', calculated_qty);
        }
    }

});


// =========================
// CUSTOMER ITEMS
// =========================
frappe.ui.form.on('Fuel Customers Items', {

    qty: function (frm) {
        calculateCustomerTotals(frm);
    },

    rate: function (frm) {
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


// =========================
// CALCULATIONS
// =========================
function calculateCustomerTotals(frm) {
    var total_qty = 0;
    var grand_total = 0;

    (frm.doc.fuel_items || []).forEach(function (item) {
        total_qty += item.qty;
        item.amount = item.qty * item.rate;
        grand_total += item.amount;
    });

    frm.set_value('total_items_qty', total_qty);
    frm.set_value('grand_items_total', grand_total);
    refresh_field('fuel_items');
}


// =========================
// DISCOUNT
// =========================
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
    calculate_percentage_discount(frm);

    let percentage_discount_value = parseFloat(frm.doc.percentge_discount);

    if (percentage_discount_value > 10) {
        frappe.msgprint(__('Percentage Discount cannot exceed 10%.'));
        return;
    }
}


// =========================
// CUSTOMER DOCUMENT CREATION (UNCHANGED LOGIC)
// =========================
function create_customer_documents(frm) {

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
            }).catch(err => reject(err));
        });
    };

    const get_new_grand_totals = (grouped_items) => {
        let new_grand_total = 0;
        for (let posting_date in grouped_items) {
            grouped_items[posting_date].forEach(item => {
                new_grand_total += item.amount;
            });
        }
        return new_grand_total;
    };

    let grouped_items = {};

    (frm.doc.fuel_items || []).forEach(item => {
        if (!grouped_items[item.posting_date]) {
            grouped_items[item.posting_date] = [];
        }
        grouped_items[item.posting_date].push(item);
    });

    let new_grand_totals = get_new_grand_totals(grouped_items);

    get_total_existing_grand_totals().then(existing_grand_totals => {

        let combined_grand_totals = existing_grand_totals + new_grand_totals;

        if (combined_grand_totals > frm.doc.grand_totals) {
            let exceeded_amount = combined_grand_totals - frm.doc.grand_totals;

            frappe.msgprint(__('The total of all Fuel Sales App ({0}) exceeds the Fuel Sales App grand total by {1}',
                [combined_grand_totals, exceeded_amount]));

            return;
        }

        for (let posting_date in grouped_items) {

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
            custDoc.net_total = 0;
            custDoc.total_qty = 0;
            custDoc.grand_totals = 0;
            custDoc.additional_discount_amount = frm.doc.additional_discount_amount;
            custDoc.fuel_sales_id = frm.doc.name;

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

                custDoc.net_total += item.amount;
                custDoc.total_qty += item.qty;
                custDoc.grand_totals += item.amount;
            });

            frappe.db.insert(custDoc).then(doc => {

                frappe.call({
                    method: "frappe.client.submit",
                    args: { doc: doc },
                    callback: function (response) {
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


// =========================
// FETCH PUMPS (UNCHANGED LOGIC)
// =========================
function fetchPumps(frm) {

    let warehousesSet = new Set();

    frappe.call({
        method: 'petro_station_app.custom_api.fetch_pumps.fetch_pumps.get_pump_or_tank',
        args: {
            date: frm.doc.date,
            employee: frm.doc.employee,
            shift: frm.doc.shift,
            station: frm.doc.station
        },
        callback: function (response) {

            if (response.message && response.message.length > 0) {

                let pumpOrTankValues = response.message;

                pumpOrTankValues.forEach(warehouse => {

                    if (!warehousesSet.has(warehouse.pump_or_tank)) {

                        warehousesSet.add(warehouse.pump_or_tank);

                        let existingItem = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);

                        if (!existingItem) {
                            let item = frm.add_child('items');
                            item.pos_profile = '';
                            item.price_list = '';
                            item.item_code = '';
                            item.meter_qtys = warehouse.qty_sold_on_meter_reading;
                            item.warehouse = warehouse.pump_or_tank;
                        } else {
                            existingItem.meter_qtys = warehouse.qty_sold_on_meter_reading;
                        }

                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'POS Profile',
                                filters: {
                                    warehouse: warehouse.pump_or_tank
                                }
                            },
                            callback: function (posResponse) {

                                if (posResponse.message) {

                                    let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);

                                    if (item) {
                                        item.pos_profile = posResponse.message.name;
                                        item.price_list = posResponse.message.selling_price_list;
                                        item.item_code = posResponse.message.custom_fuel;
                                    }

                                    frappe.call({
                                        method: 'frappe.client.get',
                                        args: {
                                            doctype: 'Item Price',
                                            filters: {
                                                item_code: item.item_code,
                                                price_list: frm.doc.price_list
                                            },
                                            fieldname: 'price_list_rate'
                                        },
                                        callback: function (priceResponse) {

                                            if (priceResponse.message) {

                                                let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);

                                                if (item) {
                                                    item.rate = priceResponse.message.price_list_rate;
                                                }

                                                frm.refresh_field('items');
                                            }
                                        }
                                    });

                                    frappe.call({
                                        method: 'petro_station_app.custom_api.fetch_pumps.fetch_pumps.get_total_qty',
                                        args: {
                                            from_date: frm.doc.date,
                                            employee: frm.doc.employee,
                                            shift: frm.doc.shift,
                                            station: frm.doc.station,
                                            pump_or_tank_list: JSON.stringify([warehouse.pump_or_tank])
                                        },
                                        callback: function (qtyResponse) {

                                            let qtySold = Number(qtyResponse.message);

                                            let item = frm.doc.items.find(item => item.warehouse === warehouse.pump_or_tank);

                                            if (item) {

                                                item.qty_sold = qtySold;

                                                if (!qtySold) {
                                                    item.actual_qty = warehouse.qty_sold_on_meter_reading;
                                                } else {
                                                    item.actual_qty = warehouse.qty_sold_on_meter_reading - qtySold;
                                                }

                                                item.qty = item.actual_qty;
                                                item.amount = item.rate * item.qty;

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
                frappe.msgprint(__('No pump or tank locations found for the selected criteria.'));
            }
        }
    });
}