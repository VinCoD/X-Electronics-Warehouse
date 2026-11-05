from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


QTY_PRECISION = Decimal("0.000001")
VALUE_PRECISION = Decimal("0.000001")
RATE_PRECISION = Decimal("0.000001")
MOVING_AVERAGE = "Moving Average"


def dec(value):
    return Decimal(str(value or 0))


def quantize(value, precision):
    return value.quantize(precision, rounding=ROUND_HALF_UP)


def get_balance(item, warehouse, posting_datetime=None, lock=False):
    """One SQL aggregate over the append-only movement history."""
    clauses = ["item = %(item)s", "warehouse = %(warehouse)s"]
    params = {"item": item, "warehouse": warehouse}
    if posting_datetime:
        clauses.append("posting_datetime <= %(posting_datetime)s")
        params["posting_datetime"] = posting_datetime
    suffix = " FOR UPDATE" if lock else ""
    rows = frappe.db.sql(
        """SELECT COALESCE(SUM(actual_qty), 0) AS qty,
                  COALESCE(SUM(stock_value_difference), 0) AS value
           FROM `tabStock Ledger Entry`
           WHERE """ + " AND ".join(clauses) + suffix,
        params,
        as_dict=True,
    )
    return dec(rows[0].qty), dec(rows[0].value)


def get_valuation_method():
    """Read the app-wide valuation choice, defaulting to Moving Average."""
    return frappe.db.get_single_value("Warehouse Settings", "valuation_method") or MOVING_AVERAGE


def lock_item_warehouse(item, warehouse):
    """Serialize postings even when the warehouse currently has no ledger rows."""
    frappe.db.sql(
        "SELECT name FROM `tabWarehouse` WHERE name = %s FOR UPDATE", warehouse
    )
    frappe.db.sql("SELECT name FROM `tabItem` WHERE name = %s FOR UPDATE", item)


def validate_leaf_warehouse(warehouse):
    if not warehouse or not frappe.db.exists("Warehouse", warehouse):
        frappe.throw(_("Select a valid warehouse."))
    doc = frappe.get_cached_doc("Warehouse", warehouse)
    if doc.disabled:
        frappe.throw(_("Warehouse {0} is disabled.").format(warehouse))
    if doc.is_group:
        frappe.throw(_("Stock can only be posted to a leaf warehouse: {0}.").format(warehouse))


def insert_ledger_entry(entry, item, warehouse, qty_delta, value_delta, qty_after, value_after, rate):
    row = frappe.get_doc({
        "doctype": "Stock Ledger Entry",
        "posting_datetime": entry.posting_datetime,
        "item": item,
        "warehouse": warehouse,
        "voucher_type": "Stock Entry",
        "voucher_no": entry.name,
        "actual_qty": float(qty_delta),
        "qty_after_transaction": float(qty_after),
        "valuation_rate": float(rate),
        "stock_value_difference": float(value_delta),
        "stock_value": float(value_after),
    })
    row.flags.from_stock_entry = True
    row.insert(ignore_permissions=True)


class StockEntry(Document):
    def validate(self):
        if self.docstatus == 0:
            self._validate_entry()

    def _validate_entry(self):
        if self.stock_entry_type not in ("Receipt", "Consume", "Transfer"):
            frappe.throw(_("Choose Receipt, Consume or Transfer."))
        if not self.items:
            frappe.throw(_("Add at least one item row."))
        if self.stock_entry_type == "Receipt":
            validate_leaf_warehouse(self.to_warehouse)
        elif self.stock_entry_type == "Consume":
            validate_leaf_warehouse(self.from_warehouse)
        else:
            validate_leaf_warehouse(self.from_warehouse)
            validate_leaf_warehouse(self.to_warehouse)
            if self.from_warehouse == self.to_warehouse:
                frappe.throw(_("Source and destination warehouses must be different."))
        posting_dt = get_datetime(self.posting_datetime)
        for row in self.items:
            if not row.item or not frappe.db.exists("Item", row.item):
                frappe.throw(_("Every row needs a valid item."))
            if frappe.db.get_value("Item", row.item, "disabled"):
                frappe.throw(_("Item {0} is disabled.").format(row.item))
            if dec(row.qty) <= 0:
                frappe.throw(_("Quantity must be greater than zero for {0}.").format(row.item))
            if self.stock_entry_type == "Receipt" and dec(row.basic_rate) < 0:
                frappe.throw(_("Unit cost cannot be negative."))
            warehouses = []
            if self.stock_entry_type in ("Consume", "Transfer"):
                warehouses.append(self.from_warehouse)
            if self.stock_entry_type in ("Receipt", "Transfer"):
                warehouses.append(self.to_warehouse)
            if frappe.db.exists("Stock Ledger Entry", {
                "item": row.item,
                "warehouse": ("in", warehouses),
                "posting_datetime": (">", posting_dt),
            }):
                frappe.throw(_("Backdated stock entries are not allowed for {0}; they would invalidate its moving-average valuation.").format(row.item))

    def on_submit(self):
        self._validate_entry()
        if get_valuation_method() != MOVING_AVERAGE:
            frappe.throw(_("Only Moving Average valuation is currently supported."))
        if self.posting_status == "Posted" or self.posting_key:
            frappe.throw(_("This Stock Entry has already been posted."))
        # Lock all involved item/warehouse pairs in deterministic order to avoid deadlocks.
        pairs = set()
        for row in self.items:
            if self.stock_entry_type in ("Consume", "Transfer"):
                pairs.add((row.item, self.from_warehouse))
            if self.stock_entry_type in ("Receipt", "Transfer"):
                pairs.add((row.item, self.to_warehouse))
        for item, warehouse in sorted(pairs):
            lock_item_warehouse(item, warehouse)

        for row in self.items:
            qty = quantize(dec(row.qty), QTY_PRECISION)
            if self.stock_entry_type == "Receipt":
                self._receipt(row, qty)
            elif self.stock_entry_type == "Consume":
                self._consume(row, qty)
            else:
                self._transfer(row, qty)

        self.db_set("posting_status", "Posted", update_modified=False)
        key = frappe.generate_hash(length=32)
        self.db_set("posting_key", key, update_modified=False)
    def _receipt(self, row, qty):
        old_qty, old_value = get_balance(row.item, self.to_warehouse)
        incoming_value = quantize(qty * dec(row.basic_rate), VALUE_PRECISION)
        new_qty = quantize(old_qty + qty, QTY_PRECISION)
        new_value = quantize(old_value + incoming_value, VALUE_PRECISION)
        rate = quantize(new_value / new_qty, RATE_PRECISION) if new_qty else Decimal(0)
        insert_ledger_entry(self, row.item, self.to_warehouse, qty, incoming_value, new_qty, new_value, rate)

    def _consume(self, row, qty):
        old_qty, old_value = get_balance(row.item, self.from_warehouse)
        self._assert_available(row.item, self.from_warehouse, old_qty, qty)
        rate = quantize(old_value / old_qty, RATE_PRECISION) if old_qty else Decimal(0)
        outgoing_value = quantize(qty * rate, VALUE_PRECISION)
        new_qty = quantize(old_qty - qty, QTY_PRECISION)
        new_value = Decimal(0) if new_qty == 0 else quantize(old_value - outgoing_value, VALUE_PRECISION)
        insert_ledger_entry(self, row.item, self.from_warehouse, -qty, -outgoing_value, new_qty, new_value, rate)

    def _transfer(self, row, qty):
        source_qty, source_value = get_balance(row.item, self.from_warehouse)
        self._assert_available(row.item, self.from_warehouse, source_qty, qty)
        source_rate = quantize(source_value / source_qty, RATE_PRECISION) if source_qty else Decimal(0)
        transfer_value = quantize(qty * source_rate, VALUE_PRECISION)
        source_new_qty = quantize(source_qty - qty, QTY_PRECISION)
        source_new_value = Decimal(0) if source_new_qty == 0 else quantize(source_value - transfer_value, VALUE_PRECISION)
        insert_ledger_entry(self, row.item, self.from_warehouse, -qty, -transfer_value, source_new_qty, source_new_value, source_rate)

        target_qty, target_value = get_balance(row.item, self.to_warehouse)
        target_new_qty = quantize(target_qty + qty, QTY_PRECISION)
        target_new_value = quantize(target_value + transfer_value, VALUE_PRECISION)
        target_rate = quantize(target_new_value / target_new_qty, RATE_PRECISION) if target_new_qty else Decimal(0)
        insert_ledger_entry(self, row.item, self.to_warehouse, qty, transfer_value, target_new_qty, target_new_value, target_rate)

    @staticmethod
    def _assert_available(item, warehouse, available, requested):
        if available - requested < 0:
            frappe.throw(_("Insufficient stock for {0} in {1}. Available: {2}; requested: {3}.").format(item, warehouse, available, requested))

    def on_cancel(self):
        frappe.throw(_("Posted Stock Entries are immutable. Correct stock using a compensating Stock Entry."))
