"""Entry point — supports:
  gitplex              # load repos from config
  gitplex .            # scan current dir for git repos
  gitplex /path/to/dir # scan that dir for git repos
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
  gitplex -h|--help     show this help
  gitplex -v|--version  show version

Key bindings (inside the app):
  c   commit          p   pull          P   push
  f   fetch           b   branch        S   stash
  n   new repo        a   add repo      C   clone repo
  R   remotes         X   remove repo   r   refresh
  q   quit
  Ctrl+P  bulk pull   Ctrl+U  bulk push Ctrl+F  bulk fetch
  Ctrl+A  select all repos
  h   toggle hunk mode (in diff view)
  s   stage hunk
"""


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


if __name__ == "__main__":
    main()
