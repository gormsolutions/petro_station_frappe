# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt

class PetroSettings(Document):
    def validate(self):
        # Validate that all required accounts exist
        self.validate_accounts()
        self.validate_email_settings()
        
    def validate_accounts(self):
        """Validate all accounts exist and are of the correct type"""
        accounts_to_check = [
            {"field": "default_cash_account", "account_type": "Cash"},
            {"field": "default_bank_account", "account_type": "Bank"},
            {"field": "default_receivable_account", "account_type": "Receivable"},
            {"field": "default_sales_account", "account_type": "Income Account"},
            {"field": "default_cogs_account", "account_type": "Cost of Goods Sold"},
            {"field": "default_expense_account", "account_type": "Expense Account"}
        ]
        
        for account in accounts_to_check:
            if not self.get(account["field"]):
                continue
                
            account_doc = frappe.get_doc("Account", self.get(account["field"]))
            if account_doc.account_type != account["account_type"]:
                frappe.throw(f"Account {self.get(account['field'])} is not of type {account['account_type']}")
    
    def validate_email_settings(self):
        """Validate email settings if notifications are enabled"""
        if (self.enable_low_stock_notifications or self.enable_shift_closure_notifications) and self.email_sender_address:
            # Check if the email format is valid
            from frappe.utils import validate_email_address
            if not validate_email_address(self.email_sender_address):
                frappe.throw(f"Invalid email format for sender address: {self.email_sender_address}")
            
            # Check CC emails if provided
            if self.notification_cc_emails:
                cc_emails = [email.strip() for email in self.notification_cc_emails.split(',')]
                for email in cc_emails:
                    if not validate_email_address(email):
                        frappe.throw(f"Invalid email format in CC list: {email}")

# Helper functions to get settings values
def get_petro_settings():
    """Get the Petro Settings document"""
    return frappe.get_single("Petro Settings")

def get_default_currency():
    """Get the default currency for petro operations"""
    settings = get_petro_settings()
    return settings.default_currency or "UGX"

def get_default_exchange_currency():
    """Get the default exchange currency for petro operations"""
    settings = get_petro_settings()
    return settings.default_exchange_currency or "USD"

def get_account(account_type):
    """
    Get a specific account based on the account type
    
    Args:
        account_type (str): One of 'cash', 'bank', 'receivable', 'sales', 'cogs', 'expense'
        
    Returns:
        str: The account name or None if not found
    """
    settings = get_petro_settings()
    account_map = {
        'cash': settings.default_cash_account,
        'bank': settings.default_bank_account,
        'receivable': settings.default_receivable_account,
        'sales': settings.default_sales_account,
        'cogs': settings.default_cogs_account,
        'expense': settings.default_expense_account
    }
    
    return account_map.get(account_type.lower())

def get_warehouse_type(warehouse_type):
    """
    Get a specific warehouse type
    
    Args:
        warehouse_type (str): One of 'stock', 'pump', 'tank', 'transit'
        
    Returns:
        str: The warehouse type or None if not found
    """
    settings = get_petro_settings()
    type_map = {
        'stock': settings.fuel_stock_warehouse_type or "Stock",
        'pump': settings.pump_warehouse_type or "Pump",
        'tank': settings.tank_warehouse_type or "Tank",
        'transit': settings.transit_warehouse_type or "Transit"
    }
    
    return type_map.get(warehouse_type.lower())

def get_fuel_item_group():
    """Get the default fuel item group"""
    settings = get_petro_settings()
    return settings.default_fuel_item_group or "Products"

# Tank and Pump Management Settings
def get_tank_level_thresholds():
    """
    Get minimum and critical tank level thresholds
    
    Returns:
        dict: Contains 'minimum' and 'critical' percentages
    """
    settings = get_petro_settings()
    return {
        'minimum': flt(settings.minimum_tank_level_percentage) / 100 if settings.minimum_tank_level_percentage else 0.15,
        'critical': flt(settings.critical_tank_level_percentage) / 100 if settings.critical_tank_level_percentage else 0.05
    }

def get_pump_variance_threshold():
    """
    Get maximum allowed pump variance percentage
    
    Returns:
        float: Maximum variance as a decimal (e.g., 0.02 for 2%)
    """
    settings = get_petro_settings()
    return flt(settings.maximum_pump_variance_percentage) / 100 if settings.maximum_pump_variance_percentage else 0.02

def is_auto_dipping_enabled():
    """Check if automated dipping entries are enabled"""
    settings = get_petro_settings()
    return cint(settings.enable_auto_dipping) == 1

# Shift Management Settings
def get_shift_settings():
    """
    Get settings related to shift management
    
    Returns:
        dict: Contains various shift management settings
    """
    settings = get_petro_settings()
    return {
        'duration_hours': cint(settings.default_shift_duration_hours) or 8,
        'require_handover': cint(settings.require_employee_handover) == 1,
        'auto_close_hours': cint(settings.auto_close_shift_after_hours) or 0,
        'gl_variance_tolerance': flt(settings.shift_gl_variance_tolerance) or 1000
    }

# Fuel Card Settings
def get_card_settings():
    """
    Get settings related to fuel cards
    
    Returns:
        dict: Contains various fuel card settings
    """
    settings = get_petro_settings()
    return {
        'credit_limit': flt(settings.default_card_credit_limit) or 10000,
        'validity_days': cint(settings.default_card_validity_days) or 365,
        'series_prefix': settings.card_series_prefix or "",
        'enable_expiry_notifications': cint(settings.enable_card_expiry_notifications) == 1
    }

# Report Settings
def get_report_settings():
    """
    Get settings related to reports
    
    Returns:
        dict: Contains various report settings
    """
    settings = get_petro_settings()
    return {
        'default_days': cint(settings.default_report_days) or 30,
        'include_canceled': cint(settings.include_canceled_transactions) == 1,
        'default_chart_type': settings.default_chart_type or "Bar",
        'limited_roles': [r.role for r in settings.disable_detailed_reports_for_roles] if settings.disable_detailed_reports_for_roles else []
    }

# Notification Settings
def get_notification_settings():
    """
    Get settings related to notifications
    
    Returns:
        dict: Contains various notification settings
    """
    settings = get_petro_settings()
    return {
        'enable_low_stock': cint(settings.enable_low_stock_notifications) == 1,
        'enable_shift_closure': cint(settings.enable_shift_closure_notifications) == 1,
        'sender_email': settings.email_sender_address or "",
        'cc_emails': [email.strip() for email in settings.notification_cc_emails.split(',')] if settings.notification_cc_emails else []
    } 