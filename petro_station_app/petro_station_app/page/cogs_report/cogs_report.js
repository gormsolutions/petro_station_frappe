frappe.pages['cogs-report'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'COGS REPORT',
        single_column: true
    });

    // Filter section — single row using flex
    let filters_area = $(`
        <div class="filters-area row" style="margin: 20px 0;">
            <div class="col-md-3"></div>
            <div class="col-md-3"></div>
        </div>
    `).appendTo(page.main);

    // From Date field
    let from_date_field = frappe.ui.form.make_control({
        df: {
            fieldtype: 'Date',
            label: 'From Date',
            fieldname: 'from_date',
            reqd: 1
        },
        parent: filters_area.find('.col-md-3').eq(0),
        render_input: true
    });

    // To Date field
    let to_date_field = frappe.ui.form.make_control({
        df: {
            fieldtype: 'Date',
            label: 'To Date',
            fieldname: 'to_date',
            reqd: 1
        },
        parent: filters_area.find('.col-md-3').eq(1),
        render_input: true
    });

    // Watch for 'To Date' value change
    to_date_field.$input.on('change', function() {
        let from_date = from_date_field.get_value();
        let to_date = to_date_field.get_value();

        if (!from_date || !to_date) {
            frappe.msgprint(__('Please select both From Date and To Date'));
            return;
        }

        console.log("To Date has been set: " + to_date);

        let filters = {
            from_date: from_date,
            to_date: to_date
        };

        // Call the Python method
        frappe.call({
            method: 'petro_station_app.custom_api.pages_reports.cogs.execute',
            args: {
                filters: JSON.stringify(filters)
            },
            callback: function(response) {
                if (response.message) {
                    render_report(response.message);
                }
            }
        });
    });

   // Render the report tables
function render_report(data) {
    const { columns, result, daily_sales_html } = data;

    // Clear any existing tables/reports before rendering new ones
    page.main.find('.report-wrapper').remove();

    // Create a wrapper for the entire report
    let report_wrapper = $('<div class="report-wrapper" style="margin-top: 30px;"></div>').appendTo(page.main);

    // === COGS Report Section ===
    let cogs_section = $('<div class="table-responsive"></div>').appendTo(report_wrapper);
    let cogs_table = $('<table class="table table-bordered table-hover"></table>').appendTo(cogs_section);

    // COGS Table Header
    let thead = $('<thead></thead>').appendTo(cogs_table);
    let header_row = $('<tr></tr>').appendTo(thead);
    columns.forEach(col => {
        $('<th>').text(col.label).appendTo(header_row);
    });

    // COGS Table Body
    let tbody = $('<tbody></tbody>').appendTo(cogs_table);
    result.forEach(row => {
        let row_html = $('<tr></tr>').appendTo(tbody);
        columns.forEach(col => {
            let value = row[col.fieldname];
            // Format currency and float fields nicely
            if (col.fieldtype === "Currency" || col.fieldtype === "Float") {
                value = frappe.format(value, { fieldtype: col.fieldtype, options: col.options });
            }
            $('<td>').html(value).appendTo(row_html);
        });
    });

    // === Daily Sales Section ===
    let sales_section = $(`
        <div class="daily-sales-section" style="margin-top: 40px;">
            <h4 style="margin-bottom: 20px;">Daily Sales Summary</h4>
            ${daily_sales_html}
        </div>
    `).appendTo(report_wrapper);
}

};
