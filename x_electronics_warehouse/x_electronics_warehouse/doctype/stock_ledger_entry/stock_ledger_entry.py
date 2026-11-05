import frappe
from frappe import _
from frappe.model.document import Document


class StockLedgerEntry(Document):
    def validate(self):
        if not self.flags.get("from_stock_entry"):
            frappe.throw(_("Stock Ledger Entries are created only by submitted Stock Entries."))

    def on_trash(self):
        frappe.throw(_("Stock Ledger Entries are immutable and cannot be deleted."))
