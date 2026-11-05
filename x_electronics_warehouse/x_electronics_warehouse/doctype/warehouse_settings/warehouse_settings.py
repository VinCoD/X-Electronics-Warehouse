import frappe
from frappe import _
from frappe.model.document import Document


class WarehouseSettings(Document):
    def validate(self):
        self.valuation_method = self.valuation_method or "Moving Average"
        if self.valuation_method != "Moving Average":
            frappe.throw(_("Only Moving Average valuation is currently supported."))
