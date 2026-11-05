#!/usr/bin/env bash
set -euo pipefail

APP_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="${FRAPPE_BENCH_DIR:-$HOME/frappe-bench}"
SITE_NAME="${FRAPPE_SITE_NAME:-warehouse.local}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-15}"

if ! grep -qi 'Ubuntu' /etc/os-release || ! grep -q '24.04' /etc/os-release; then
  echo "This bootstrap targets Ubuntu 24.04 under WSL 2. Current OS: $(. /etc/os-release && echo "$PRETTY_NAME")" >&2
  exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl build-essential python3-dev python3.12-dev python3.12-venv \
  python3-pip pkg-config libffi-dev libssl-dev libmariadb-dev \
  mariadb-server mariadb-client redis-server xvfb libfontconfig1 \
  libxrender1 libxext6 cron rsync

sudo systemctl enable --now mariadb redis-server

if ! command -v nvm >/dev/null 2>&1 && [[ ! -s "$HOME/.nvm/nvm.sh" ]]; then
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
export NVM_DIR="$HOME/.nvm"
# shellcheck source=/dev/null
source "$NVM_DIR/nvm.sh"
nvm install 20
nvm alias default 20
nvm use 20
npm install --global yarn

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

if ! command -v bench >/dev/null 2>&1; then
  uv tool install frappe-bench
fi

if [[ ! -d "$BENCH_DIR/apps/frappe" ]]; then
  bench init --frappe-branch "$FRAPPE_BRANCH" --python python3.12 "$BENCH_DIR"
elif [[ ! -x "$BENCH_DIR/env/bin/python" ]]; then
  echo "Found $BENCH_DIR, but it has no bench Python environment. Remove that incomplete bench or set FRAPPE_BENCH_DIR." >&2
  exit 1
fi

APP_BENCH_PATH="$BENCH_DIR/apps/x_electronics_warehouse"
install -d "$APP_BENCH_PATH"
rsync -a --delete --exclude='.git' "$APP_SOURCE/" "$APP_BENCH_PATH/"

# The workspace checkout is not a Git clone. Install/register it locally instead
# of asking Bench to clone it from a remote repository.
(cd "$BENCH_DIR" && bench pip install -e "apps/x_electronics_warehouse")
python3 "$APP_SOURCE/env/normalize_apps.py" "$BENCH_DIR/sites/apps.txt"
(cd "$BENCH_DIR" && bench build --app x_electronics_warehouse)

bash "$APP_SOURCE/env/setup_site.sh" "$BENCH_DIR" "$SITE_NAME"

echo
echo "Setup complete. Start the local site with: cd '$BENCH_DIR' && bench start"
echo "Site URL: http://localhost:8000 (default site: $SITE_NAME)"
