import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required."))
    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be after To Date."))
    conditions = ["sle.posting_datetime >= %(from_datetime)s", "sle.posting_datetime < %(to_datetime)s"]
    params = {
        "from_datetime": f"{filters.from_date} 00:00:00",
        "to_datetime": f"{frappe.utils.add_days(filters.to_date, 1)} 00:00:00",
    }
    for field in ("item", "warehouse"):
        if filters.get(field):
            conditions.append(f"sle.{field} = %({field})s")
            params[field] = filters[field]
    columns = [
        {"label": _("Posting Date"), "fieldname": "posting_datetime", "fieldtype": "Datetime", "width": 155},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Link", "options": "DocType", "width": 125},
        {"label": _("Voucher"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
        {"label": _("Qty Change"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Balance Qty"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 110},
        {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Value Change"), "fieldname": "stock_value_difference", "fieldtype": "Currency", "width": 115},
        {"label": _("Balance Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 115},
    ]
    rows = frappe.db.sql(
        """SELECT sle.posting_datetime, sle.item, sle.warehouse, sle.voucher_type,
                  sle.voucher_no, sle.actual_qty, sle.qty_after_transaction,
                  sle.valuation_rate, sle.stock_value_difference, sle.stock_value
           FROM `tabStock Ledger Entry` sle WHERE """ + " AND ".join(conditions) +
        " ORDER BY sle.posting_datetime, sle.creation, sle.name",
        params,
        as_dict=True,
    )
    return columns, rows
