# Local Frappe environment (Windows + WSL 2)

Frappe Bench needs a Linux service environment (MariaDB, Redis, Node/Yarn and Python build dependencies). On this Windows workstation, use Ubuntu in WSL 2; the app folder itself stays in the Windows workspace and is copied into the Linux filesystem before bench installation for better filesystem performance.

## First setup

1. In PowerShell, run `wsl --install -d Ubuntu-24.04`. Restart Windows if prompted and launch Ubuntu once to complete its first-run setup.
2. In Ubuntu, change to your cloned project directory and run:

   ```bash
   cd /path/to/X-Electronics-Warehouse
   bash env/setup_wsl.sh
   ```

The installer uses Ubuntu 24.04, Frappe v15, MariaDB, Redis, Node.js 20, Yarn, and `uv`/`frappe-bench`. It creates `~/frappe-bench`, provisions a local `warehouse.local` site with a generated local database root password saved in `~/frappe-bench/.local-db-root-password`, installs this workspace checkout as an editable Python package, registers it with the bench, and runs `bench --site warehouse.local run-tests --app x_electronics_warehouse`. The generated password is for this disposable local development database; do not reuse it elsewhere.

The v15 Frappe source checkout, Python virtual environment, database files, Redis processes, and bench are all stored/managed inside WSL. The script copies the app to `~/frappe-bench/apps/x_electronics_warehouse` before installing it.

## After setup

Start the site in Ubuntu with:

```bash
cd ~/frappe-bench
bench start
```

Open `http://localhost:8000` in Windows (the bench serves `warehouse.local` as its default site). In a second Ubuntu shell, commands can be run with:

```bash
cd ~/frappe-bench
bench --site warehouse.local run-tests --app x_electronics_warehouse
bench --site warehouse.local migrate
```

## Refresh the installed app from the project directory

After making app edits, run this from the project directory in Ubuntu:

```bash
APP_SOURCE="$PWD"
rsync -a --delete --exclude='.git' "$APP_SOURCE/" ~/frappe-bench/apps/x_electronics_warehouse/
cd ~/frappe-bench
bench --site warehouse.local migrate
bench --site warehouse.local run-tests --app x_electronics_warehouse
```

`rsync --delete` targets only the bench app copy. Do not point it at the workspace or a different directory.
