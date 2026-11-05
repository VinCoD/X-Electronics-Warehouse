frappe.ui.form.on("Stock Entry", {
  refresh(frm) {
    frm.set_query("from_warehouse", () => ({ filters: { is_group: 0, disabled: 0 } }));
    frm.set_query("to_warehouse", () => ({ filters: { is_group: 0, disabled: 0 } }));
  }
});
