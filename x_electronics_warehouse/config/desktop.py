from frappe import _


def get_data():
    return [{"label": _("Stock"), "items": [
        {"type": "doctype", "name": "Item", "label": _("Item")},
        {"type": "doctype", "name": "Warehouse", "label": _("Warehouse")},
        {"type": "doctype", "name": "Stock Entry", "label": _("Stock Entry")},
        {"type": "report", "name": "Stock Ledger", "label": _("Stock Ledger"), "doctype": "Stock Ledger Entry"},
        {"type": "report", "name": "Stock Balance", "label": _("Stock Balance"), "doctype": "Stock Ledger Entry"},
    ]}]
