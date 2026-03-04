"""Entry point — supports:
  gitplex              # load repos from config
  gitplex .            # scan current dir for git repos
  gitplex /path/to/dir # scan that dir for git repos
  gitplex <url>        # clone repo and add to config
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
  gitplex <url>         clone repo, add to config, and open
  gitplex <url> --dest <path>  clone to a specific directory
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

_URL_PREFIXES = ("https://", "http://", "git@", "git://", "ssh://")


def _is_url(s: str) -> bool:
    return s.startswith(_URL_PREFIXES)


def _repo_name_from_url(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repo"


def _cmd_clone(args: list[str]) -> None:
    from .git.repo import GitRepo
    from .config import Config

    url = args[0]
    dest: Path | None = None

    if "--dest" in args:
        idx = args.index("--dest")
        if idx + 1 >= len(args):
            print("Error: --dest requires a path argument", file=sys.stderr)
            sys.exit(1)
        dest = Path(args[idx + 1]).expanduser().resolve()
    else:
        dest = Path.cwd() / _repo_name_from_url(url)

    print(f"Cloning {url} → {dest} ...")
    try:
        repo, msg = GitRepo.clone(url, dest)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if msg:
        print(msg)

    Config().add_repo(repo.path)

    from .app import GitUIApp
    GitUIApp().run()


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
            print("gitplex 0.3.0")
        return

    if args and _is_url(args[0]):
        _cmd_clone(args)
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
