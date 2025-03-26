import frappe
from frappe import _
from frappe.model.document import Document
import frappe.sessions

class CashRefund(Document):

    def on_submit(self):
        self.create_journal_entries()

    def add_journal_entry_row(self, journal_entry, account, debit, credit, cost_center=None, set_party=False):
        # Prepare row data
        row = {
            'account': account,
            'debit_in_account_currency': debit,
            'credit_in_account_currency': credit,
            'cost_center': cost_center,
            'user_remark': self.remarks
        }

        # Set party and party type only on the debit side (when set_party is True)
        if set_party:
            row['party_type'] = "Customer"
            row['party'] = self.customer

        # Append row to journal entry
        journal_entry.append('accounts', row)

    @frappe.whitelist()
    def create_journal_entries(self):
        try:
            # Fetch investment accounts based on transaction type
            accounts = self.get_investment_accounts()

            # Create a Journal Entry for payment if applicable
            if self.make_payments == 1:
                journal_entry_payment = frappe.new_doc('Journal Entry')
                journal_entry_payment.voucher_type = 'Journal Entry'
                journal_entry_payment.company = accounts['company_set']
                journal_entry_payment.posting_date = self.date
                journal_entry_payment.user_remark = self.remarks
                journal_entry_payment.custom_cash_refund_id = self.name

                # Add debit entry (set_party=True for debit side)
                self.add_journal_entry_row(journal_entry_payment, accounts['debit_account'], self.grand_totals, 0, cost_center=self.station, set_party=True)
                
                # Add credit entry (set_party=False for credit side)
                self.add_journal_entry_row(journal_entry_payment, accounts['credit_account'], 0, self.grand_totals, cost_center=self.station, set_party=False)

                # Insert and submit journal entry
                journal_entry_payment.insert()
                journal_entry_payment.submit()
                frappe.msgprint(_("Payment Journal Entry created successfully: {0}").format(journal_entry_payment.name))

        except Exception as e:
            frappe.log_error(message=str(e), title=_("Failed to create Journal Entry"))
            frappe.throw(_("Failed to create Journal Entry: {0}").format(str(e)))

    def get_investment_accounts(self):
        # Fetch account details from Cash Refund Settings for the logged-in user
        user = frappe.session.user  # Corrected 'sessions' to 'session'

        # Query to get account details
        cash_refund_account = frappe.db.sql(""" 
            SELECT debit_account, credit_account, debit_cash_account, company, commission_account
            FROM `tabCash Refund Settings`
            WHERE user = %s
            LIMIT 1
        """, (user,), as_dict=True)

        if not cash_refund_account:
            frappe.throw(_("Cash Refund Account details not found in Cash Refund Settings for the current user."))

        return {
            'debit_account': cash_refund_account[0]['debit_account'],
            'company_set': cash_refund_account[0]['company'],
            'credit_account': cash_refund_account[0]['credit_account'],
            'commission_account': cash_refund_account[0]['commission_account'],
            'debit_cash_account': cash_refund_account[0]['debit_cash_account'],
        }
