"""Git repository wrapper — subprocess-based for reliability."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ──────────────────────────── Data models ───────────────────────────────────

@dataclass
class FileStatus:
    path: str
    staged: str   # X in 'XY' of git status --porcelain
    unstaged: str # Y

    @property
    def is_staged(self) -> bool:
        return self.staged not in (" ", "?")

    @property
    def is_unstaged(self) -> bool:
        return self.unstaged not in (" ", "?")

    @property
    def is_untracked(self) -> bool:
        return self.staged == "?" and self.unstaged == "?"

    @property
    def status_label(self) -> str:
        if self.is_untracked:
            return "?"
        parts = []
        if self.staged not in (" ", "?"):
            parts.append(self.staged)
        if self.unstaged not in (" ", "?"):
            parts.append(self.unstaged.lower())
        return "".join(parts) or " "


@dataclass
class RepoStatus:
    path: Path
    branch: str
    ahead: int
    behind: int
    files: list[FileStatus] = field(default_factory=list)
    error: str = ""

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_dirty(self) -> bool:
        return bool(self.files)

    @property
    def staged_files(self) -> list[FileStatus]:
        return [f for f in self.files if f.is_staged]

    @property
    def unstaged_files(self) -> list[FileStatus]:
        return [f for f in self.files if f.is_unstaged or f.is_untracked]


@dataclass
class CommitInfo:
    sha: str
    short_sha: str
    author: str
    date: str
    subject: str
    refs: str = ""


# ──────────────────────────── GitRepo class ──────────────────────────────────

class GitRepo:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()

    # ── Low-level helpers ────────────────────────────────────────────────────

    def _run(self, *args: str, check: bool = True, input: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            check=check,
            input=input or None,
        )

    @classmethod
    def is_git_repo(cls, path: Path) -> bool:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--git-dir"],
            capture_output=True,
        )
        return r.returncode == 0

    # ── Status ───────────────────────────────────────────────────────────────

    def get_branch(self) -> str:
        r = self._run("branch", "--show-current", check=False)
        return r.stdout.strip() or "HEAD"

    def get_ahead_behind(self) -> tuple[int, int]:
        r = self._run("rev-list", "--left-right", "--count", "HEAD...@{upstream}", check=False)
        if r.returncode == 0 and r.stdout.strip():
            parts = r.stdout.strip().split()
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        return 0, 0

    def get_file_statuses(self) -> list[FileStatus]:
        r = self._run("status", "--porcelain=v1", "-u", check=False)
        files: list[FileStatus] = []
        for line in r.stdout.splitlines():
            if len(line) >= 3:
                x, y, path = line[0], line[1], line[3:]
                if " -> " in path:
                    path = path.split(" -> ")[1]
                files.append(FileStatus(path=path, staged=x, unstaged=y))
        return files

    def get_status(self) -> RepoStatus:
        try:
            branch = self.get_branch()
            ahead, behind = self.get_ahead_behind()
            files = self.get_file_statuses()
            return RepoStatus(path=self.path, branch=branch, ahead=ahead,
                              behind=behind, files=files)
        except Exception as e:
            return RepoStatus(path=self.path, branch="?", ahead=0, behind=0, error=str(e))

    # ── Diff ─────────────────────────────────────────────────────────────────

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> str:
        args = ["diff"]
        if staged:
            args.append("--staged")
        args.extend(["--"])
        if file_path:
            args.append(file_path)
        r = self._run(*args, check=False)
        return r.stdout

    def get_diff_stat(self) -> str:
        r = self._run("diff", "--stat", check=False)
        return r.stdout.strip()

    # ── Staging ──────────────────────────────────────────────────────────────

    def stage_file(self, file_path: str) -> tuple[bool, str]:
        r = self._run("add", "--", file_path, check=False)
        return r.returncode == 0, r.stderr.strip()

    def unstage_file(self, file_path: str) -> tuple[bool, str]:
        r = self._run("restore", "--staged", "--", file_path, check=False)
        if r.returncode != 0:
            r = self._run("reset", "HEAD", "--", file_path, check=False)
        return r.returncode == 0, r.stderr.strip()

    def stage_all(self) -> tuple[bool, str]:
        r = self._run("add", "-A", check=False)
        return r.returncode == 0, r.stderr.strip()

    def unstage_all(self) -> tuple[bool, str]:
        r = self._run("reset", "HEAD", check=False)
        return r.returncode == 0, r.stderr.strip()

    def apply_hunk_patch(self, patch: str) -> tuple[bool, str]:
        """Apply a single-hunk patch to the index."""
        r = subprocess.run(
            ["git", "-C", str(self.path), "apply", "--cached", "--unidiff-zero", "-"],
            input=patch,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            # Retry without --unidiff-zero
            r = subprocess.run(
                ["git", "-C", str(self.path), "apply", "--cached", "-"],
                input=patch,
                capture_output=True,
                text=True,
            )
        return r.returncode == 0, r.stderr.strip()

    def discard_file(self, file_path: str) -> tuple[bool, str]:
        r = self._run("checkout", "--", file_path, check=False)
        return r.returncode == 0, r.stderr.strip()

    # ── Commit ───────────────────────────────────────────────────────────────

    def commit(self, message: str) -> tuple[bool, str]:
        r = self._run("commit", "-m", message, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    # ── Remote operations ────────────────────────────────────────────────────

    def pull(self) -> tuple[bool, str]:
        r = self._run("pull", "--rebase=false", check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def has_upstream(self) -> bool:
        r = self._run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
        return r.returncode == 0

    def push(self) -> tuple[bool, str]:
        if self.has_upstream():
            r = self._run("push", check=False)
        else:
            # First push — set upstream automatically
            branch = self.get_branch()
            remotes = self.list_remotes()
            remote_name = remotes[0][0] if remotes else "origin"
            r = self._run("push", "-u", remote_name, branch, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def fetch(self) -> tuple[bool, str]:
        r = self._run("fetch", "--all", "--prune", check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def force_push(self) -> tuple[bool, str]:
        """Push with --force-with-lease (safe force: fails if remote was updated by someone else)."""
        if self.has_upstream():
            r = self._run("push", "--force-with-lease", check=False)
        else:
            branch = self.get_branch()
            remotes = self.list_remotes()
            remote_name = remotes[0][0] if remotes else "origin"
            r = self._run("push", "--force-with-lease", "-u", remote_name, branch, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    # ── Init ─────────────────────────────────────────────────────────────────

    @classmethod
    def init(cls, path: Path, initial_branch: str = "main") -> tuple["GitRepo", str]:
        """Run git init in path (creates dir if needed). Returns (repo, message)."""
        path = Path(path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["git", "-C", str(path), "init", f"--initial-branch={initial_branch}"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # older git doesn't support --initial-branch
            r = subprocess.run(
                ["git", "-C", str(path), "init"],
                capture_output=True, text=True,
            )
        msg = (r.stdout + r.stderr).strip()
        return cls(path), msg

    # ── Clone ────────────────────────────────────────────────────────────────

    @classmethod
    def clone(cls, url: str, dest: Path) -> tuple["GitRepo", str]:
        """Clone a remote repo to dest. Returns (repo, output_message)."""
        dest = Path(dest).expanduser().resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["git", "clone", url, str(dest)],
            capture_output=True, text=True,
        )
        msg = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            raise RuntimeError(msg)
        return cls(dest), msg

    # ── Log / Graph ──────────────────────────────────────────────────────────

    def get_log_graph(self, max_count: int = 80) -> str:
        r = self._run(
            "log",
            "--graph",
            "--oneline",
            "--decorate",
            "--all",
            f"--max-count={max_count}",
            "--color=never",
            check=False,
        )
        return r.stdout

    def get_log(self, max_count: int = 50) -> list[CommitInfo]:
        fmt = "%H\x1f%h\x1f%an\x1f%ar\x1f%s\x1f%D"
        r = self._run("log", f"--format={fmt}", f"--max-count={max_count}", check=False)
        commits = []
        for line in r.stdout.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 6:
                commits.append(CommitInfo(
                    sha=parts[0], short_sha=parts[1],
                    author=parts[2], date=parts[3],
                    subject=parts[4], refs=parts[5],
                ))
        return commits

    # ── History operations ───────────────────────────────────────────────────

    def get_head_sha(self) -> str:
        r = self._run("rev-parse", "HEAD", check=False)
        return r.stdout.strip()

    def cherry_pick(self, sha: str) -> tuple[bool, str]:
        r = self._run("cherry-pick", sha, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def revert(self, sha: str) -> tuple[bool, str]:
        r = self._run("revert", "--no-edit", sha, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def reset(self, sha: str, mode: str = "mixed") -> tuple[bool, str]:
        """mode: soft | mixed | hard"""
        r = self._run("reset", f"--{mode}", sha, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    def amend(self, message: str) -> tuple[bool, str]:
        r = self._run("commit", "--amend", "-m", message, check=False)
        return r.returncode == 0, (r.stdout + r.stderr).strip()

    # ── Stash ────────────────────────────────────────────────────────────────

    def stash(self, message: str = "") -> tuple[bool, str]:
        args = ["stash", "push"]
        if message:
            args += ["-m", message]
        r = self._run(*args, check=False)
        return r.returncode == 0, r.stderr.strip()

    def stash_pop(self) -> tuple[bool, str]:
        r = self._run("stash", "pop", check=False)
        return r.returncode == 0, r.stderr.strip()

    def stash_list(self) -> list[str]:
        r = self._run("stash", "list", check=False)
        return r.stdout.splitlines()

    # ── Branches ─────────────────────────────────────────────────────────────

    def list_branches(self) -> list[str]:
        r = self._run("branch", "-a", "--format=%(refname:short)", check=False)
        return [b.strip() for b in r.stdout.splitlines() if b.strip()]

    def checkout(self, branch: str) -> tuple[bool, str]:
        r = self._run("checkout", branch, check=False)
        return r.returncode == 0, r.stderr.strip()

    def checkout_new_branch(self, name: str) -> tuple[bool, str]:
        r = self._run("checkout", "-b", name, check=False)
        return r.returncode == 0, r.stderr.strip()

    # ── Remotes ──────────────────────────────────────────────────────────────

    def get_remote_url(self, name: str = "origin") -> str:
        r = self._run("remote", "get-url", name, check=False)
        return r.stdout.strip()

    def list_remotes(self) -> list[tuple[str, str]]:
        """Return list of (name, url) for all remotes."""
        r = self._run("remote", "-v", check=False)
        seen: dict[str, str] = {}
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and "(fetch)" in line:
                seen[parts[0]] = parts[1]
        return list(seen.items())

    def add_remote(self, name: str, url: str) -> tuple[bool, str]:
        r = self._run("remote", "add", name, url, check=False)
        return r.returncode == 0, r.stderr.strip()

    def set_remote_url(self, name: str, url: str) -> tuple[bool, str]:
        r = self._run("remote", "set-url", name, url, check=False)
        return r.returncode == 0, r.stderr.strip()

    def remove_remote(self, name: str) -> tuple[bool, str]:
        r = self._run("remote", "remove", name, check=False)
        return r.returncode == 0, r.stderr.strip()
