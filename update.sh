#!/usr/bin/env bash
# GitPlex — updater
# Re-installs the package from the local source into the existing venv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/.local/share/gitplex/venv"

green() { printf '\033[32m%s\033[0m\n' "$*"; }
cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }
die()   { printf '\033[31m%s\033[0m\n' "Error: $*"; exit 1; }

[[ -d "$VENV" ]] || die "GitPlex is not installed. Run install.sh first."

cyan "Updating GitPlex from $SCRIPT_DIR …"
"$VENV/bin/pip" install --quiet --force-reinstall "$SCRIPT_DIR"

VERSION=$("$VENV/bin/python" -m gitplex.main --version 2>/dev/null || echo "unknown")
green "Done. $VERSION"
