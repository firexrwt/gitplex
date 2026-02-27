#!/usr/bin/env bash
# GitPlex — uninstaller
set -euo pipefail

INSTALL_DIR="$HOME/.local/share/gitplex"
BIN_CMD="$HOME/.local/bin/gitplex"

green() { printf '\033[32m%s\033[0m\n' "$*"; }
cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }

echo ""
cyan "Uninstalling GitPlex…"

[[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR" && cyan "Removed $INSTALL_DIR"
[[ -f "$BIN_CMD"     ]] && rm -f  "$BIN_CMD"     && cyan "Removed $BIN_CMD"

# Remove installer lines from RC files
for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile"; do
    [[ -f "$rc" ]] || continue
    if grep -q "Added by GitPlex installer" "$rc" 2>/dev/null; then
        # Remove the comment + export line pair
        sed -i '/# Added by GitPlex installer/{N;d}' "$rc"
        cyan "Cleaned $rc"
    fi
done

echo ""
green "✓ GitPlex uninstalled."
