// Copyright (c) 2025, mututa paul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Monthly Report", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Monthly Report', {
    before_save: async function(frm) {
        await fetchAllData(frm);  // Fetch data before saving
       
    },
    // Trigger when the 'to_date' field is changed
    to_date: function(frm) {
        // Call the function to populate the stock entries
        populateChildTableWithQuantities(frm);
        average_rate_function(frm)
    },
    station_manager: function(frm) {
        // Call the function to populate the stock entries
        populateChildTableWithQuantities(frm);
        average_rate_function(frm)
    },
    user: function(frm) {
        // Call the function to populate the stock entries
        populateChildTableWithQuantities(frm);
    }

});

async function fetchAllData(frm) {
    await Promise.all([
        fetchExpenditures(frm),
        fetchMeterReadings(frm),
        fetchTankTotals(frm)
    ]);
}

async function fetchExpenditures(frm) {
    return new Promise((resolve) => {
        frappe.call({
            method: "petro_station_app.custom_api.transaction_report.stock_report.fetch_expenditures",
            args: {
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                station: frm.doc.station
            },
            callback: function(r) {
                if (r.message) {
                    let data = r.message.station_expenses;
                    frm.clear_table("expenditure");
                    
                    let total_qty = 0;
                    for (let expense of data) {
                        for (let item of expense.items) {
                            let row = frm.add_child("expenditure");
                            Object.assign(row, {
                                expense_name: expense.expense_name,
                                expense_date: expense.expense_date,
                                description: item.description,
                                claim_type: item.claim_type,
                                amount: item.amount,
                                party: item.party
                            });
                            total_qty += item.amount;
                        }
                    }
                    frm.set_value('grand_totals_expenditure', total_qty);
                    frm.refresh_field("expenditure");
                }
                resolve();
            }
        });
    });
}

async function fetchMeterReadings(frm) {
    return new Promise((resolve) => {
        frappe.call({
            method: "petro_station_app.custom_api.transaction_report.stock_report.meter_reading",
            args: {
                end_date_previous_month: frm.doc.end_date_previous_month,
                end_date_current_month: frm.doc.end_date_current_month,
                station: frm.doc.station
            },
            callback: function(r) {
                if (r.message) {
                    let data = r.message;
                    console.log(data)
                    frm.clear_table("meter_reading_report_items");

                    let processedPumps = new Set(); // Set to track processed pumps
                    let previousMonthData = {}; // Store previous month's closing readings
                    let totalSalesExpected = 0; // Variable to store the sum of all sales_expected

                    // Process the data for the previous month
                    for (let reading of data) {
                        if (reading.from_date === frm.doc.end_date_previous_month) {
                            for (let item of reading.items) {
                                previousMonthData[item.pump_or_tank] = item.closing_meter_reading;
                            }
                        }
                    }

                    // Now process the data for the current month
                    for (let reading of data) {
                        if (reading.from_date === frm.doc.end_date_current_month) {
                            for (let item of reading.items) {
                                if (processedPumps.has(item.pump_or_tank)) {
                                    continue;
                                }

                                let row = frm.add_child("meter_reading_report_items");

                                row.pump_or_tank = item.pump_or_tank;

                                let opening = previousMonthData[item.pump_or_tank] || 0;
                                let closing = item.closing_meter_reading || 0;

                                row.opening_meter_reading = opening;
                                row.closing_meter_reading = closing;

                                // Calculate and set the sales_expected
                                row.sales_expected = closing - opening;
                                
                                // Add the difference to the total
                                totalSalesExpected += row.sales_expected;

                                processedPumps.add(item.pump_or_tank);
                            }
                        }
                    }

                    // Set the total sales_expected in the totals field
                    frm.set_value('totals_sales_expected', totalSalesExpected);

                    frm.refresh_field("meter_reading_report_items");
                }
                resolve();
            }
        });
    });
}


async function fetchTankTotals(frm) {
    return new Promise((resolve) => {
        frappe.call({
            method: "petro_station_app.custom_api.transaction_report.stock_report.get_totals_tanks",
            args: {
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                station: frm.doc.station
            },
            callback: function(r) {
                if (r.message) {
                    let data = r.message;
                    frm.clear_table("dipping_totals_tanks_items");

                    for (let [tank, dipping_difference] of Object.entries(data)) {
                        let row = frm.add_child("dipping_totals_tanks_items");
                        Object.assign(row, {
                            tank: tank,
                            dipping_difference: dipping_difference
                        });
                    }

                    frm.refresh_field("dipping_totals_tanks_items");
                }
                resolve();
            }
        });
    });
}

function populateChildTableWithQuantities(frm) {
    // Fetch the start_date, end_date, and user from the form
    const start_date = frm.doc.from_date;  // Adjust field names as per your form
    const end_date = frm.doc.to_date;
    const user = frm.doc.user;  // Adjust as needed if user is passed

    // Call the server-side method to get stock ledger entries
    frappe.call({
        method: "petro_station_app.custom_api.stock_monthly_repo.gas_daily_repo.get_stock_ledger_entries",  // Use the correct path to your Python function
        args: {
            start_date: start_date,
            end_date: end_date,
            user: user
        },
        callback: function(r) {
            console.log(r);
            if (r.message) {
                // Extract total paid and unpaid quantities from the response
                const totalPaidQty = r.message.total_paid_qty;
                const totalUnpaidQty = r.message.total_unpaid_qty;

                // Clear existing rows in the child table before populating
                frm.clear_table('daily_sales_items');

                // Create a map to store item-wise data
                let groupedData = {};

                // Function to update or add item in groupedData
                function addOrUpdateItem(item_code, warehouse, qty, type) {
                    let key = `${item_code}|${warehouse}`;

                    if (!groupedData[key]) {
                        groupedData[key] = { item_code, warehouse, total_paid_qty: 0, total_unpaid_qty: 0, total_qty: 0 };
                    }

                    if (type === "paid") {
                        groupedData[key].total_paid_qty += Math.abs(qty);
                    } else {
                        groupedData[key].total_unpaid_qty += Math.abs(qty);
                    }

                    // Update the total_qty (sum of paid and unpaid)
                    groupedData[key].total_qty = groupedData[key].total_paid_qty + groupedData[key].total_unpaid_qty;
                }

                // Process total paid quantities
                $.each(totalPaidQty, function(key, value) {
                    let [item_code, warehouse] = key.split('|');
                    addOrUpdateItem(item_code, warehouse, value, "paid");
                });

                // Process total unpaid quantities
                $.each(totalUnpaidQty, function(key, value) {
                    let [item_code, warehouse] = key.split('|');
                    addOrUpdateItem(item_code, warehouse, value, "unpaid");
                });

                // Populate child table with combined data
                for (const key in groupedData) {
                    let data = groupedData[key];

                    let row = frm.add_child('daily_sales_items');
                    row.item_code = data.item_code;
                    row.warehouse = data.warehouse;
                    row.total_paid_qty = data.total_paid_qty;
                    row.total_unpaid_qty = data.total_unpaid_qty;
                    row.total_qty = data.total_qty; // Summed value
                }

                // Refresh the child table to display the updated rows
                frm.refresh_field('daily_sales_items');
            }
        }
    });
}

function average_rate_function(frm) {
    // Your logic or function goes here
    console.log("The to_date field has been set!");

    // You can call your Python function using frappe.call as needed
    frappe.call({
        method: 'petro_station_app.custom_api.stock_monthly_repo.gas_daily_repo.get_average_selling_price_by_filters', // Adjust the path to your function
        args: {
            user: frm.doc.station_manager,  // Pass user if needed
            start_date: frm.doc.start_date,  // Pass start date if needed
            end_date: frm.doc.to_date  // Use the 'to_date' as the end_date
        },
        callback: function(r) {
            if (r.message) {
                // Assuming you want to populate the child table as well
                frm.clear_table('average_rate_items_tab');

                r.message.forEach(function(item) {
                    let row = frm.add_child('average_rate_items_tab');
                    row.item_code = item.item_code;
                    // row.item_group = item.item_group;
                    row.average_sales_rate = item.average_sales_rate;
                    row.warehouse = item.warehouse;
                });

                frm.refresh_field('average_rate_items_tab');
            }
        }
    });
}




