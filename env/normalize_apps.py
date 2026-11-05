"""Normalize a Bench apps.txt file and repair the bootstrap's old concat typo."""

from pathlib import Path
import sys


apps_file = Path(sys.argv[1])
apps = [line.strip() for line in apps_file.read_text().splitlines() if line.strip()]
normalized = []
for app in apps:
    if app == "frappex_electronics_warehouse":
        normalized.extend(["frappe", "x_electronics_warehouse"])
    elif app not in normalized:
        normalized.append(app)

if "frappe" not in normalized:
    normalized.insert(0, "frappe")
if "x_electronics_warehouse" not in normalized:
    normalized.append("x_electronics_warehouse")

apps_file.write_text("\n".join(normalized) + "\n")
