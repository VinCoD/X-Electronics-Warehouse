from frappe.model.document import Document


class Item(Document):
    def validate(self):
        self.valuation_method = "Moving Average"
