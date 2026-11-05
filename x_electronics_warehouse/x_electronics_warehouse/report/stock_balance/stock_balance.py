import frappe
from frappe import _
from frappe.utils import add_days


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("as_of_date"):
        frappe.throw(_("As of Date is required."))
    conditions = ["sle.posting_datetime < %(cutoff)s"]
    params = {"cutoff": f"{add_days(filters.as_of_date, 1)} 00:00:00"}
    for field in ("item", "warehouse"):
        if filters.get(field):
            conditions.append(f"sle.{field} = %({field})s")
            params[field] = filters[field]
    columns = [
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 165},
        {"label": _("Quantity"), "fieldname": "qty", "fieldtype": "Float", "width": 110},
        {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 125},
        {"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 125},
    ]
    rows = frappe.db.sql(
        """SELECT sle.item, i.item_name, sle.warehouse,
                  SUM(sle.actual_qty) AS qty,
                  SUM(sle.stock_value_difference) AS stock_value,
                  CASE WHEN SUM(sle.actual_qty) = 0 THEN 0
                       ELSE SUM(sle.stock_value_difference) / SUM(sle.actual_qty) END AS valuation_rate
           FROM `tabStock Ledger Entry` sle
           INNER JOIN `tabItem` i ON i.name = sle.item
           WHERE """ + " AND ".join(conditions) +
        " GROUP BY sle.item, i.item_name, sle.warehouse "
        "HAVING ABS(SUM(sle.actual_qty)) > 0.0000005 OR ABS(SUM(sle.stock_value_difference)) > 0.0000005 "
        "ORDER BY i.item_name, sle.warehouse",
        params,
        as_dict=True,
    )
    return columns, rows
