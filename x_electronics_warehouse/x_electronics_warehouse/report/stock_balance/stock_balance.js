frappe.query_reports["Stock Balance"] = {
  filters: [
    { fieldname: "as_of_date", label: __("As of Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
    { fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Item" },
    { fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" }
  ]
};
