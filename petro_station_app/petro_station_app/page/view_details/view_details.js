frappe.pages['view-details'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Detailed Report',
        single_column: true
    });

    // Add filters to the page
    const accountField = page.add_field({
        label: 'Account',
        fieldtype: 'Link',
        options: 'Account',
        fieldname: 'account_name',
        reqd: 1
    });

    const stationField = page.add_field({
        label: 'Station',
        fieldtype: 'Link',
        options: 'Cost Center',
        fieldname: 'cost_center',
        reqd: 1
    });

    const fromDateField = page.add_field({
        label: 'From Date',
        fieldtype: 'Date',
        fieldname: 'from_date'
    });

    const toDateField = page.add_field({
        label: 'To Date',
        fieldtype: 'Date',
        fieldname: 'to_date'
    });

    // Add button to fetch transactions
    const fetchButton = page.add_button(__('Fetch Transactions'), function() {
        fetchDetails(); // Call the function when the button is clicked
    });

    // Prefill account_name if available in the route parameters
    const route = frappe.get_route();
    const accountNameParam = route && route[1]?.account_name;

    if (accountNameParam) {
        accountField.set_value(accountNameParam);
    }

    // Create a container to display results
    const resultContainer = $('<div>').appendTo(page.body);

    // Number formatter for UGX (Ugandan Shillings)
    const formatUGX = new Intl.NumberFormat('en-UG', {
        style: 'currency',
        currency: 'UGX',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    // Function to fetch and display data
    function fetchDetails() {
        // Clear the container before displaying new results
        resultContainer.empty();

        // Get values from filters
        const accountName = accountField.get_value();
        const fromDate = fromDateField.get_value();
        const toDate = toDateField.get_value();
        const costCenter = stationField.get_value();

        // Validate the required fields
        if (!accountName) {
            frappe.msgprint(__('Please enter an account name'));
            return;
        }

        // Fetch data from the server
        frappe.call({
            method: "petro_station_app.custom_api.transaction_report.view_details.fetch_transactions",
            args: {
                account_name: accountName,
                from_date: fromDate,
                to_date: toDate,
                station: costCenter
            },
            callback: function (response) {
                const transactions = response.message || [];
                let totalDebit = 0;
                let totalCredit = 0;

                // Display a message if no transactions are found
                if (transactions.length === 0) {
                    frappe.msgprint(__('No transactions found.'));
                    return;
                }

                // Calculate totals first
                transactions.forEach(trx => {
                    totalDebit += trx.debit || 0;
                    totalCredit += trx.credit || 0;
                });

                // Generate the HTML table for transactions
                const results = `
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th colspan="2"><strong>Total</strong></th>
                                <th><strong>${formatUGX.format(totalDebit)}</strong></th>
                                <th><strong>${formatUGX.format(totalCredit)}</strong></th>
                                <th><strong>${formatUGX.format(totalDebit - totalCredit)}</strong></th>
                                <th colspan="3"></th>
                            </tr>
                            <tr>
                                <th>Posting Date</th>
                                <th>Account</th>
                                <th>Debit</th>
                                <th>Credit</th>
                                <th>Difference (Debit - Credit)</th>
                                <th>Voucher Type</th>
                                <th>Voucher No</th>
                                <th>Voucher Subtype</th>
                                <th>Employer/Party</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${transactions.map(trx => {
                                const debit = trx.debit || 0;
                                const credit = trx.credit || 0;
                                const difference = debit - credit;

                                // Dynamically create the link for Voucher No based on voucher type
                                const voucherLink = `/app/${trx.voucher_type.toLowerCase().replace(' ', '-')}/${trx.voucher_no}`;

                                // Use the employee full name if available
                                const partyOrEmployer = trx.employee_name || 'N/A';

                                return `
                                    <tr>
                                        <td>${trx.posting_date || ''}</td>
                                        <td>${trx.account || ''}</td>
                                        <td>${formatUGX.format(debit)}</td>
                                        <td>${formatUGX.format(credit)}</td>
                                        <td>${formatUGX.format(difference)}</td>
                                        <td>${trx.voucher_type || ''}</td>
                                        <td><a href="${voucherLink}" target="_blank">${trx.voucher_no || ''}</a></td>
                                        <td>${trx.voucher_subtype || ''}</td>
                                        <td>${partyOrEmployer}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                `;

                // Render the table in the container
                resultContainer.html(results);
            },
            error: function (err) {
                frappe.msgprint(__('An error occurred while fetching transactions. Please try again.'));
                console.error('Error fetching transactions:', err);
            }
        });
    }

    // Trigger data fetch when any field value changes
    accountField.$input.on('change', fetchDetails);
    stationField.$input.on('change', fetchDetails);
    fromDateField.$input.on('change', fetchDetails);
    toDateField.$input.on('change', fetchDetails);
};
