frappe.query_reports["Stock Ledger"] = {
  filters: [
    { fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
    { fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
    { fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Item" },
    { fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" }
  ]
};
