import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	old_name = "Warehouse"
	new_name = "X Electronics WMS"

	if not frappe.db.exists("Workspace", old_name):
		return

	if frappe.db.exists("Workspace", new_name):
		frappe.delete_doc(
			"Workspace", old_name, force=True, ignore_permissions=True
		)
	else:
		rename_doc(
			"Workspace",
			old_name,
			new_name,
			force=True,
			ignore_permissions=True,
			show_alert=False,
		)
