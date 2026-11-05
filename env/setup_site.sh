#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${1:?Usage: setup_site.sh BENCH_DIR SITE_NAME}"
SITE_NAME="${2:?Usage: setup_site.sh BENCH_DIR SITE_NAME}"
DB_ROOT_PASSWORD_FILE="$BENCH_DIR/.local-db-root-password"
export PATH="$HOME/.local/bin:$PATH"

if [[ ! -f "$DB_ROOT_PASSWORD_FILE" ]]; then
  umask 077
  openssl rand -hex 24 > "$DB_ROOT_PASSWORD_FILE"
fi
DB_ROOT_PASSWORD="$(cat "$DB_ROOT_PASSWORD_FILE")"
if [[ "${SKIP_DB_ROOT_SETUP:-0}" != "1" ]]; then
  sudo bash "$(dirname "${BASH_SOURCE[0]}")/configure_mariadb_root.sh" "$DB_ROOT_PASSWORD_FILE"
fi

cd "$BENCH_DIR"

if ! bench --site "$SITE_NAME" list-apps >/dev/null 2>&1; then
  if [[ -e "$BENCH_DIR/sites/$SITE_NAME/site_config.json" ]]; then
    echo "Site $SITE_NAME has partial setup files. Inspect it before removing the partial site and rerunning." >&2
    exit 1
  fi
  bench new-site "$SITE_NAME" --db-host 127.0.0.1 --db-root-username root --mariadb-root-password "$DB_ROOT_PASSWORD" --admin-password "$(openssl rand -hex 24)"
fi

if ! bench --site "$SITE_NAME" list-apps | grep -qx 'x_electronics_warehouse'; then
  bench --site "$SITE_NAME" install-app x_electronics_warehouse
fi

bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" set-config allow_tests true
bench --site "$SITE_NAME" run-tests --app x_electronics_warehouse
