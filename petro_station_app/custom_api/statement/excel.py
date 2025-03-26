import frappe
from openpyxl import Workbook # type: ignore
from io import BytesIO

@frappe.whitelist(allow_guest=True)
def download_xlsx(doctype, name):
    # Fetch the document
    document = frappe.get_doc(doctype, name)

    # Create a new Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Statement Report"

    # === ADD STATEMENT SUMMARY ===
    ws.append(["Field", "Value"])
    summary_fields = [
        ("Statement Name", document.name),
        ("Customer", document.customer),
        ("Customer Name", document.customer_name),
        ("From Date", document.from_date),
        ("To Date", document.to_date),
        ("Balance Forward", document.balance_forward),
        ("Total Paid", document.total_paid),
        ("Total Invoices", document.total_invoices),
        ("Total Outstanding", document.total_outstanding_amount),
    ]

    for field, value in summary_fields:
        ws.append([field, value])

    # Add a blank row before child table
    ws.append([])

    # === ADD STATEMENT DETAILS (CHILD TABLE) ===
    if hasattr(document, "statement_details") and document.statement_details:
        # Add headers
        detail_headers = [
            "Invoice Date", "Invoice No", "Vehicle No", "Item Code", "Quantity",
            "Rate", "Amount", "Paid Amount", "Running Balance",
            "Credit Sales ID", "Station Invoice", "Sales Invoice No"
        ]
        ws.append(detail_headers)

        # Add child table data
        for item in document.statement_details:
            ws.append([
                item.get("invoice_date", ""),
                item.get("invoice_no", ""),
                item.get("vehicle_no", ""),
                item.get("item_code", ""),
                item.get("qty", 0),
                item.get("rate", 0),
                item.get("amount", 0),
                item.get("paid_amount", 0),
                item.get("running_balance", 0),
                item.get("credit_sales_id", ""),
                item.get("station_inv", ""),
                item.get("sales_invoice_no", "")
            ])
    else:
        ws.append(["No statement details found"])

    # Save to a buffer
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    # Return response as an Excel file
    frappe.local.response.filecontent = file_stream.read()
    frappe.local.response.type = "binary"
    frappe.local.response.filename = f"{name}.xlsx"
