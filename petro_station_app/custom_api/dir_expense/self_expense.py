import frappe  # type: ignore
from frappe import _  # type: ignore
from frappe.utils import now  # type: ignore

@frappe.whitelist()
def create_self_expense(
    amount=None,  # Made optional by assigning default value
    description=None,  # Made optional by assigning default value
    pesu_amount=None,
    pecu_amount=None,
    customer_reference_no=None,
    supplier_reference_no=None,
    pay_supplier=None,
    mop=None,
    receive_customer=None
):
    user = frappe.session.user
    expense_setting = frappe.get_doc("Expense Settings", {"user": user})
    
    if not expense_setting:
        return {"message": _("Expense settings not found for the user.")}

    # Create and submit a new Station Expenses document only if amount and description are provided
    if amount and description:
        station_expense = frappe.get_doc({
            "doctype": "Station Expenses",
            "employee": expense_setting.party,
            "mode_of_payment": expense_setting.mode_of_payment,
            "date": now(),
            "items": [
                {
                    "party_type": expense_setting.party_type,
                    "party": expense_setting.party,
                    "amount": amount,
                    "description": description,
                    "claim_type": expense_setting.claim_type,
                }
            ]
        })
        station_expense.insert()
        station_expense.submit()

    # Create a Payment Entry for Supplier if provided
    if pay_supplier and mop and pesu_amount:
        create_payment_entry(
            payment_type="Pay",
            party_type="Supplier",
            party=pay_supplier,
            amount=pesu_amount,
            mode_of_payment=mop,
            supplier_reference_no=supplier_reference_no
        )

    # Create a Payment Entry for Customer if provided
    if mop and receive_customer and pecu_amount:
        create_payment_entry(
            payment_type="Receive",
            party_type="Customer",
            party=receive_customer,
            amount=pecu_amount,
            mode_of_payment=mop,
            customer_reference_no=customer_reference_no
        )

    return {"message": _("Station Expenses document and payment entries submitted successfully.")}

def create_payment_entry(payment_type, party_type, party, amount, mode_of_payment, customer_reference_no=None, supplier_reference_no=None):
    """Create and submit a Payment Entry with separate reference numbers for Customer and Supplier."""

    company = frappe.defaults.get_user_default("Company")
    account = frappe.get_value("Mode of Payment Account", {
        "parent": mode_of_payment,
        "company": company
    }, "default_account")

    if not account:
        frappe.throw(_("No default account found for Mode of Payment {0} and Company {1}").format(mode_of_payment, company))

    # Decide reference number based on party type
    if party_type == "Customer":
        reference_no = customer_reference_no
    elif party_type == "Supplier":
        reference_no = supplier_reference_no
    else:
        reference_no = None

    payment_entry_data = {
        "doctype": "Payment Entry",
        "payment_type": payment_type,
        "party_type": party_type,
        "party": party,
        "paid_amount": amount,
        "received_amount": amount,
        "mode_of_payment": mode_of_payment,
        "posting_date": now(),
        "reference_no": reference_no,
        "reference_date": now(),
        "company": company
    }

    if payment_type == "Receive":
        payment_entry_data["paid_to"] = account
    elif payment_type == "Pay":
        payment_entry_data["paid_from"] = account
    elif payment_type == "Internal Transfer":
        payment_entry_data["paid_from"] = account

    payment_entry = frappe.get_doc(payment_entry_data)
    payment_entry.insert()
    payment_entry.submit()

import frappe
from frappe.utils import flt
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

import frappe
from frappe.utils import getdate, flt
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

@frappe.whitelist()
def get_profit_and_loss(from_date, to_date, company, cost_center=None):
    # Ensure date format
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # Prepare filters for the report
    filters = frappe._dict({
        "from_date": from_date,
        "to_date": to_date,
        "company": company,
        "accumulated_values": 0,
        "filter_based_on": "Date Range",
        "period_start_date": from_date,
        "period_end_date": to_date,
        "presentation_currency": frappe.db.get_value("Company", company, "default_currency"),
        "periodicity": "Monthly"
    })

    # Handle cost_center (accepts a list but expects a single value)
    if cost_center:
        if isinstance(cost_center, list):
            filters.cost_center = cost_center[0]  # Take the first one only if it's a list
        else:
            filters.cost_center = cost_center

    try:
        # Debug log to check filters
        frappe.logger().info(f"Filters for Profit and Loss: {filters}")

        # Execute the report query
        result = execute(filters)

        # Check if the result is a tuple and has at least two elements (columns and data)
        if isinstance(result, tuple) and len(result) >= 2:
            columns, data = result[:2]
        else:
            frappe.throw("Unexpected result format from execute")

        # Debug log to check result
        frappe.logger().info(f"Profit and Loss result columns: {columns}")
        frappe.logger().info(f"Profit and Loss result data: {data}")

        # Initialize variables for income, expenses, and net profit calculation
        income = []
        expenses = []
        net_profit = 0.0

        # Loop through the data to categorize and calculate income and expenses
        for row in data:
            if row.get("parent_account") == "Income":
                income.append(row)
                net_profit += flt(row.get("amount"))
            elif row.get("parent_account") == "Expense":
                expenses.append(row)
                net_profit -= flt(row.get("amount"))

        return {
            "filters_used": filters,
            "income": income,
            "expenses": expenses,
            "net_profit": net_profit
        }

    except Exception as e:
        # In case of errors, log and raise the error with a helpful message
        frappe.logger().error(f"Error fetching Profit and Loss data: {str(e)}")
        frappe.throw(f"Error occurred: {str(e)}")
