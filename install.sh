#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  GitPlex — installer                                              ║
# ║  Installs into ~/.local/share/gitplex/venv                        ║
# ║  Creates ~/.local/bin/gitplex command                             ║
# ╚══════════════════════════════════════════════════════════════════╝
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/gitplex"
BIN_DIR="$HOME/.local/bin"
VENV="$INSTALL_DIR/venv"

# ── Colour helpers ────────────────────────────────────────────────────────────
red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n'  "$*"; }
die()   { red "✗  $*"; exit 1; }
ok()    { green "✓  $*"; }
info()  { cyan "→  $*"; }

# ── Find Python 3.11+ ─────────────────────────────────────────────────────────
PYTHON=""
for py in python3.14 python3.13 python3.12 python3.11 python3 python; do
    if command -v "$py" &>/dev/null 2>&1; then
        if "$py" -c 'import sys; exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
            PYTHON="$py"
            break
        fi
    fi
done
[[ -n "$PYTHON" ]] || die "Python 3.11+ not found. Install it and re-run."

PY_VER=$("$PYTHON" -c 'import sys; print(".".join(map(str,sys.version_info[:3])))')

# ── Print header ──────────────────────────────────────────────────────────────
echo ""
bold "   ██████╗ ██╗████████╗██████╗ ██╗     ███████╗██╗  ██╗"
bold "  ██╔════╝ ██║╚══██╔══╝██╔══██╗██║     ██╔════╝╚██╗██╔╝"
bold "  ██║  ███╗██║   ██║   ██████╔╝██║     █████╗   ╚███╔╝ "
bold "  ██║   ██║██║   ██║   ██╔═══╝ ██║     ██╔══╝   ██╔██╗ "
bold "  ╚██████╔╝██║   ██║   ██║     ███████╗███████╗██╔╝ ██╗"
bold "   ╚═════╝ ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝"
echo ""
info "Python   : $PY_VER"
info "Venv     : $VENV"
info "Command  : $BIN_DIR/gitplex"
echo ""

# ── Create dirs ───────────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# ── Create / reuse venv ───────────────────────────────────────────────────────
if [[ -d "$VENV" ]]; then
    info "Updating existing venv…"
else
    info "Creating virtual environment…"
    "$PYTHON" -m venv "$VENV"
fi

# ── Install package ───────────────────────────────────────────────────────────
info "Installing GitPlex and dependencies…"
"$VENV/bin/pip" install --quiet --upgrade pip wheel
"$VENV/bin/pip" install --quiet "$SCRIPT_DIR"
echo ""
ok "Package installed."

# ── Write wrapper script ──────────────────────────────────────────────────────
info "Creating 'gitplex' command at $BIN_DIR/gitplex …"
cat > "$BIN_DIR/gitplex" <<WRAPPER
#!/usr/bin/env bash
exec "$VENV/bin/python" -m gitplex.main "\$@"
WRAPPER
chmod +x "$BIN_DIR/gitplex"
ok "Command created."

# ── Ensure ~/.local/bin is in PATH ────────────────────────────────────────────
# We write to every RC file we find to cover bash AND zsh installs.
PATH_EXPORT='export PATH="$HOME/.local/bin:$PATH"'
PATH_COMMENT="# Added by GitPlex installer"
ADDED_TO=()

for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile"; do
    [[ -f "$rc" ]] || continue
    # Skip if the bin dir is already exported in this file
    if grep -qE '(^|;)\s*export PATH.*\.local/bin' "$rc" 2>/dev/null; then
        continue
    fi
    printf '\n%s\n%s\n' "$PATH_COMMENT" "$PATH_EXPORT" >> "$rc"
    ADDED_TO+=("$rc")
done

# Also create ~/.bashrc if it doesn't exist at all
if [[ ! -f "$HOME/.bashrc" ]] && [[ ${#ADDED_TO[@]} -eq 0 ]]; then
    printf '%s\n%s\n' "$PATH_COMMENT" "$PATH_EXPORT" > "$HOME/.bashrc"
    ADDED_TO+=("$HOME/.bashrc")
fi

if [[ ${#ADDED_TO[@]} -gt 0 ]]; then
    ok "Added ~/.local/bin to PATH in: ${ADDED_TO[*]}"
else
    info "~/.local/bin already in PATH (no RC files modified)."
fi

# Make available in the current shell session too
export PATH="$BIN_DIR:$PATH"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
green "══════════════════════════════════════════════"
green "  GitPlex installed successfully! 🎉"
green "══════════════════════════════════════════════"
echo ""
echo "  Usage:"
echo "    gitplex               # open with saved repos"
echo "    gitplex .             # scan current dir for repos"
echo "    gitplex ~/projects    # scan any directory"
echo ""
echo "  Reload your shell to make sure the command is available:"
echo "    source ~/.bashrc    # (or ~/.zshrc)"
echo ""
