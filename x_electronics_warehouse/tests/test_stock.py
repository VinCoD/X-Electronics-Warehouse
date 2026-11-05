import frappe
from frappe.tests.utils import FrappeTestCase

from x_electronics_warehouse.x_electronics_warehouse.doctype.stock_entry.stock_entry import get_balance
from x_electronics_warehouse.x_electronics_warehouse.report.stock_balance.stock_balance import execute as stock_balance
from x_electronics_warehouse.x_electronics_warehouse.report.stock_ledger.stock_ledger import execute as stock_ledger


class TestWarehouseStock(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.db.exists("Warehouse", "Test Root"):
            frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Test Root", "is_group": 1}).insert()
        if not frappe.db.exists("Warehouse", "Test Store"):
            frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Test Store", "parent_warehouse": "Test Root", "is_group": 0}).insert()
        cls.warehouse = "Test Store"

    def make_item(self):
        code = frappe.generate_hash(length=10)
        return frappe.get_doc({
            "doctype": "Item", "item_code": code, "item_name": f"Test Item {code}", "stock_uom": "Unit",
        }).insert().name

    def make_entry(self, entry_type, item, qty, rate=0, source=None, target=None, posting=None):
        doc = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": entry_type,
            "posting_datetime": posting or frappe.utils.now_datetime(),
            "from_warehouse": source,
            "to_warehouse": target,
            "items": [{"item": item, "qty": qty, "basic_rate": rate}],
        })
        doc.insert()
        doc.submit()
        return doc

    def test_moving_average_receipts_and_consumption(self):
        item = self.make_item()
        self.make_entry("Receipt", item, 10, 100, target=self.warehouse)
        self.make_entry("Receipt", item, 20, 120, target=self.warehouse)
        qty, value = get_balance(item, self.warehouse)
        self.assertAlmostEqual(float(qty), 30, places=5)
        self.assertAlmostEqual(float(value), 3400, places=5)

        self.make_entry("Consume", item, 15, source=self.warehouse)
        qty, value = get_balance(item, self.warehouse)
        self.assertAlmostEqual(float(qty), 15, places=5)
        self.assertAlmostEqual(float(value), 1700, places=4)
        row = frappe.db.get_value(
            "Stock Ledger Entry", {"item": item, "warehouse": self.warehouse, "actual_qty": -15},
            ["valuation_rate", "stock_value_difference"], as_dict=True,
        )
        self.assertAlmostEqual(row.valuation_rate, 113.333333, places=4)
        self.assertAlmostEqual(row.stock_value_difference, -1700, places=4)

    def test_transfer_uses_source_carrying_cost(self):
        destination = frappe.get_doc({
            "doctype": "Warehouse", "warehouse_name": f"Test Store {frappe.generate_hash(length=5)}",
            "parent_warehouse": "Test Root", "is_group": 0,
        }).insert().name
        item = self.make_item()
        self.make_entry("Receipt", item, 10, 50, target=self.warehouse)
        self.make_entry("Transfer", item, 4, source=self.warehouse, target=destination)
        self.assertEqual(float(get_balance(item, self.warehouse)[0]), 6)
        target_qty, target_value = get_balance(item, destination)
        self.assertEqual(float(target_qty), 4)
        self.assertAlmostEqual(float(target_value), 200, places=5)

    def test_insufficient_stock_is_rejected(self):
        item = self.make_item()
        self.make_entry("Receipt", item, 1, 20, target=self.warehouse)
        doc = frappe.get_doc({
            "doctype": "Stock Entry", "stock_entry_type": "Consume",
            "posting_datetime": frappe.utils.now_datetime(), "from_warehouse": self.warehouse,
            "items": [{"item": item, "qty": 2}],
        }).insert()
        with self.assertRaises(frappe.ValidationError):
            doc.submit()

    def test_group_warehouse_cannot_receive_stock(self):
        item = self.make_item()
        doc = frappe.get_doc({
            "doctype": "Stock Entry", "stock_entry_type": "Receipt",
            "posting_datetime": frappe.utils.now_datetime(), "to_warehouse": "Test Root",
            "items": [{"item": item, "qty": 1, "basic_rate": 10}],
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert()

    def test_reports(self):
        item = self.make_item()
        self.make_entry("Receipt", item, 3, 25, target=self.warehouse)
        ledger_columns, ledger_rows = stock_ledger({
            "from_date": frappe.utils.today(), "to_date": frappe.utils.today(),
            "item": item, "warehouse": self.warehouse,
        })
        self.assertTrue(ledger_columns)
        self.assertGreaterEqual(len(ledger_rows), 1)
        balance_columns, balance_rows = stock_balance({
            "as_of_date": frappe.utils.today(), "item": item, "warehouse": self.warehouse,
        })
        self.assertTrue(balance_columns)
        self.assertEqual(len(balance_rows), 1)
        self.assertAlmostEqual(float(balance_rows[0].qty), 3, places=5)
        self.assertAlmostEqual(float(balance_rows[0].stock_value), 75, places=5)
