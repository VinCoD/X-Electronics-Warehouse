#!/usr/bin/env bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "Run this helper through sudo so it can configure the local MariaDB root account." >&2
  exit 1
fi

password_file="${1:?Usage: configure_mariadb_root.sh PASSWORD_FILE}"
db_root_password="$(cat "$password_file")"

mariadb -uroot -p"$db_root_password" <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '$db_root_password';
# Frappe uses TCP for its database manager, so grant the same local password to
# the loopback host account as well as configuring socket login above.
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '$db_root_password';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY '$db_root_password';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL
