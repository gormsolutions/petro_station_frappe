import frappe
from frappe.model.document import Document

@frappe.whitelist(allow_guest=True)
def cancel_doc_and_delete_linked_docs(docname, doctype):
    try:
        # Fetch the main document quickly
        doc = frappe.get_doc(doctype, docname)

        # Check if document exists and is not already canceled
        if not doc or doc.docstatus == 2:  # 2 means canceled
            return {"message": "Document is already canceled or not found."}

        # Fast check for linked documents (Before canceling the main document)
        linked_docs = get_linked_documents(docname, doctype)
        
        if linked_docs:
            # If linked documents exist, process them before canceling the main document
            for linked_doc in linked_docs:
                try:
                    # Fetch and process the linked document
                    linked_doc_doc = frappe.get_doc(linked_doc["doctype"], linked_doc["docname"])

                    # Cancel and delete linked document if not already canceled
                    if linked_doc_doc.docstatus != 2:
                        linked_doc_doc.cancel()
                        # linked_doc_doc.delete()

                except Exception as e:
                    frappe.log_error(message=str(e), title="Error canceling linked document")
        
        # Cancel the main document only after checking linked documents
        doc.cancel()

        return {"message": "success"}

    except Exception as e:
        return {"message": f"Error: {str(e)}"}


def get_linked_documents(docname, doctype):
    """
    Retrieve linked documents based on the provided docname and doctype.
    This function checks for attachments or linked entries quickly.
    """
    linked_docs = []

    if doctype == 'Fuel Sales App':
        # Fast SQL query to check for linked documents
        linked_docs = frappe.db.sql("""
            SELECT doctype, docname
            FROM `tabFuel Sales App Linked Docs`
            WHERE parent_docname = %s
        """, (docname,), as_dict=True)

    elif doctype == 'Credit Sales App':
        # Fast SQL query to check for linked documents
        linked_docs = frappe.db.sql("""
            SELECT doctype, docname
            FROM `tabCredit Sales App Linked Docs`
            WHERE parent_docname = %s
        """, (docname,), as_dict=True)

    return linked_docs
