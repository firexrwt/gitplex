"""Entry point — supports:
  gitplex              # load repos from config
  gitplex .            # scan current dir for git repos
  gitplex /path/to/dir # scan that dir for git repos
  gitplex update       # pull latest changes and reinstall
"""
from __future__ import annotations

import sys
from pathlib import Path


_HELP = """\
gitplex — multi-repo git TUI on steroids

Usage:
  gitplex               open with repos saved in config
  gitplex .             scan current directory for git repos
  gitplex <path>        scan <path> for git repos
  gitplex update        pull latest changes and reinstall
  gitplex -h|--help     show this help
  gitplex -v|--version  show version

Key bindings (inside the app):
  c   commit          p   pull          P   push
  F   force push      f   fetch         b   branch
  S   stash           n   new repo      a   add repo
  C   clone repo      R   remotes       X   remove repo
  r   refresh         q   quit
  Ctrl+P  bulk pull   Ctrl+U  bulk push Ctrl+F  bulk fetch
  Ctrl+A  select all repos
  h   toggle hunk mode (in diff view)
  s   stage hunk
  Enter   commit actions (in Log tab)
"""

_SOURCE_DIR_FILE = Path.home() / ".config" / "gitplex" / "source_dir"


def _cmd_update() -> None:
    import subprocess

    if not _SOURCE_DIR_FILE.exists():
        print("Error: source directory not recorded. Re-run install.sh first.", file=sys.stderr)
        sys.exit(1)

    source_dir = Path(_SOURCE_DIR_FILE.read_text().strip())
    update_script = source_dir / "update.sh"

    if not update_script.exists():
        print(f"Error: update.sh not found in {source_dir}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(["bash", str(update_script)])
    sys.exit(result.returncode)


def main():
    from .app import GitUIApp

    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(_HELP)
        return

    if args and args[0] in ("-v", "--version"):
        from importlib.metadata import version as _v
        try:
            print(f"gitplex {_v('gitplex')}")
        except Exception:
            print("gitplex 0.2.0")
        return

    if args and args[0] == "update":
        _cmd_update()
        return

    scan_dir: Path | None = None

    if args:
        candidate = Path(args[0]).expanduser().resolve()
        if candidate.is_dir():
            scan_dir = candidate
        else:
            print(f"Error: not a directory: {args[0]}", file=sys.stderr)
            print("Run 'gitplex --help' for usage.", file=sys.stderr)
            sys.exit(1)

    app = GitUIApp(scan_dir=scan_dir)
    app.run()

    # After exit: print update hint if updates were found during the session
    try:
        from .config import Config
        cfg = Config()
        n = cfg.pending_updates
        if n > 0:
            print(f"\n  {n} GitPlex update{'s' if n != 1 else ''} available."
                  f"  Run: gitplex update\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
