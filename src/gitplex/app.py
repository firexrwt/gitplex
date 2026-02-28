"""GitUIApp — main Textual application."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, TabbedContent, TabPane, Label, DataTable
from textual import on, work

from .config import Config
from .git.repo import GitRepo, RepoStatus
from .git.diff import parse_diff
from .widgets.repo_list import RepoList
from .widgets.file_list import FileList
from .widgets.diff_view import DiffView
from .widgets.graph_view import GraphView
from .widgets.modals import (
    CommitModal, AddRepoModal, NewRepoModal, CloneModal, RemoteModal,
    BulkProgressModal, BranchModal, CommitActionsModal, ConfirmModal,
)


class GitUIApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "GitUI"
    SUB_TITLE = "multi-repo git TUI"

    BINDINGS = [
        # Navigation
        Binding("tab",       "focus_next",     "Next panel",    show=False),
        Binding("shift+tab", "focus_previous", "Prev panel",    show=False),
        # Per-repo actions
        Binding("c",     "commit",       "Commit",      priority=True),
        Binding("p",     "pull",         "Pull",        priority=True),
        Binding("P",     "push",         "Push",        priority=True),
        Binding("F",     "force_push",   "Force Push",  priority=True),
        Binding("f",     "fetch",        "Fetch",       priority=True),
        Binding("b",     "branch",       "Branch",      priority=True),
        Binding("S",     "stash",        "Stash",       priority=True),
        # File list
        Binding("space", "toggle_stage", "Stage/Unstage", priority=True),
        Binding("A",     "stage_all",    "Stage all",   priority=True),
        Binding("U",     "unstage_all",  "Unstage all", priority=True),
        Binding("d",     "discard",      "Discard",     priority=True),
        # Diff view
        Binding("h", "toggle_hunk_mode", "Hunk mode",   priority=True),
        Binding("s", "stage_hunk",       "Stage hunk",  priority=True),
        Binding("j", "scroll_down",      "Scroll down", priority=True, show=False),
        Binding("k", "scroll_up",        "Scroll up",   priority=True, show=False),
        Binding("g", "scroll_home",      "Top",         priority=True, show=False),
        Binding("G", "scroll_end",       "Bottom",      priority=True, show=False),
        # Bulk actions
        Binding("ctrl+p", "bulk_pull",  "Bulk Pull"),
        Binding("ctrl+u", "bulk_push",  "Bulk Push"),
        Binding("ctrl+f", "bulk_fetch", "Bulk Fetch"),
        Binding("ctrl+a", "select_all", "Select all"),
        # Repo management
        Binding("a", "add_repo",    "Add repo",    priority=True),
        Binding("n", "new_repo",    "New repo",    priority=True),
        Binding("C", "clone_repo",  "Clone",       priority=True),
        Binding("R", "remotes",     "Remotes",     priority=True),
        Binding("X", "remove_repo", "Remove repo", priority=True),
        Binding("r", "refresh",     "Refresh",     priority=True),
        Binding("q", "quit",        "Quit",        priority=True),
        Binding("enter", "commit_action", "Actions", priority=True, show=False),
    ]

    def __init__(self, scan_dir: Optional[Path] = None):
        super().__init__()
        self.config = Config()
        self._scan_dir = scan_dir          # auto-scan root (if passed via CLI)
        self._current_repo: Optional[GitRepo] = None
        self._current_file_staged: bool = False

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            # ── Left column ──────────────────────────────────────────────────
            with Vertical(id="left-col"):
                yield RepoList(id="repo-list")
                yield FileList(id="file-list")
            # ── Right column ─────────────────────────────────────────────────
            with TabbedContent(id="right-tabs"):
                with TabPane("Diff",  id="tab-diff"):
                    yield DiffView(id="diff-view")
                with TabPane("Graph", id="tab-graph"):
                    yield GraphView(id="graph-view")
        yield Footer()

    # ── Startup ───────────────────────────────────────────────────────────────

    def on_mount(self):
        if self._scan_dir:
            self._auto_scan(self._scan_dir)
        self.refresh_all()
        self._check_for_updates()
        # Auto-refresh local status every 5 seconds
        self.set_interval(5, self._auto_refresh)

    @work(thread=True)
    def _check_for_updates(self):
        """Once per day: fetch origin on the source repo and notify if behind."""
        import time, subprocess as sp
        _DAY = 86_400
        if time.time() - self.config.last_update_check < _DAY:
            return
        source_dir = self.config.source_dir
        if not source_dir or not GitRepo.is_git_repo(source_dir):
            return
        try:
            sp.run(
                ["git", "-C", str(source_dir), "fetch", "--quiet", "origin"],
                capture_output=True, timeout=10,
            )
            r = sp.run(
                ["git", "-C", str(source_dir), "rev-list", "--count", "HEAD..@{upstream}"],
                capture_output=True, text=True, timeout=5,
            )
            count = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 0
        except Exception:
            return
        self.config.set_last_update_check(time.time())
        self.config.set_pending_updates(count)
        if count > 0:
            msg = f"{count} new commit{'s' if count != 1 else ''} — run `gitplex update`"
            self.call_from_thread(
                self.notify, msg, title="GitPlex update available", timeout=5,
            )

    def _auto_refresh(self):
        """Silently refresh all repo statuses and the current repo's files."""
        self.refresh_all()
        if self._current_repo:
            self._refresh_current_repo()

    def _auto_scan(self, root: Path):
        """Add all immediate child directories that are git repos."""
        added = 0
        try:
            for child in sorted(root.iterdir()):
                if child.is_dir() and GitRepo.is_git_repo(child):
                    if self.config.add_repo(child):
                        added += 1
        except PermissionError:
            pass
        if added:
            self.notify(f"Found {added} git repos in {root.name}/", title="Auto-scan")

    # ── Refresh ───────────────────────────────────────────────────────────────

    @work(thread=True)
    def refresh_all(self):
        """Reload status for every repo in config (runs in background thread)."""
        statuses: list[RepoStatus] = []
        for path in self.config.repos:
            if path.exists():
                statuses.append(GitRepo(path).get_status())
            else:
                statuses.append(RepoStatus(path=path, branch="?",
                                           ahead=0, behind=0,
                                           error="path not found"))
        self.call_from_thread(self._apply_statuses, statuses)

    def _apply_statuses(self, statuses: list[RepoStatus]):
        self.query_one("#repo-list", RepoList).load(statuses)

    @work(thread=True)
    def _refresh_current_repo(self):
        if not self._current_repo:
            return
        status = self._current_repo.get_status()
        self.call_from_thread(self._apply_current_status, status)

    def _apply_current_status(self, status: RepoStatus):
        repo_list = self.query_one("#repo-list", RepoList)
        repo_list.update_status(status.path, status)
        file_list = self.query_one("#file-list", FileList)
        file_list.load(status.staged_files, status.unstaged_files, status.path)

    # ── Repo selection ────────────────────────────────────────────────────────

    @on(RepoList.RepoSelected)
    def _on_repo_selected(self, event: RepoList.RepoSelected):
        self._current_repo = GitRepo(event.path)
        self.sub_title = f"{event.path.name}  [{event.status.branch}]"
        file_list = self.query_one("#file-list", FileList)
        file_list.load(
            event.status.staged_files,
            event.status.unstaged_files,
            event.path,
        )
        # Clear diff/graph until user picks a file
        self.query_one("#diff-view", DiffView).clear()
        self._load_graph()

    @work(thread=True)
    def _load_graph(self):
        if not self._current_repo:
            return
        graph = self._current_repo.get_log_graph(self.config.max_log_entries)
        commits = self._current_repo.get_log(self.config.max_log_entries)
        self.call_from_thread(
            self.query_one("#graph-view", GraphView).show_graph,
            graph, commits,
        )

    # ── Commit actions ────────────────────────────────────────────────────────

    def action_commit_action(self) -> None:
        """Open commit actions modal for the highlighted row in the Log table."""
        focused = self.focused
        if not isinstance(focused, DataTable) or focused.id != "commit-table":
            return
        if not self._current_repo:
            return
        row_idx = focused.cursor_row
        if row_idx is None:
            return
        gv = self.query_one("#graph-view", GraphView)
        commits = list(gv._commits.values())
        if row_idx >= len(commits):
            return
        commit = commits[row_idx]
        head_sha = self._current_repo.get_head_sha()
        is_head = commit.sha == head_sha
        repo = self._current_repo

        def _execute(result) -> None:
            action = result.action
            if action == "cherry-pick":
                ok, out = repo.cherry_pick(result.sha)
            elif action == "revert":
                ok, out = repo.revert(result.sha)
            elif action.startswith("reset-"):
                ok, out = repo.reset(result.sha, mode=action[6:])
            elif action == "amend":
                ok, out = repo.amend(result.message)
            else:
                return
            label = action.replace("-", " ").title()
            if ok:
                self.notify(out.splitlines()[0] if out else "Done",
                            title=f"{label} ✓")
            else:
                self.notify(out.splitlines()[0] if out else "Failed",
                            title=f"{label} ✗", severity="error")
            self._refresh_current_repo()
            self._load_graph()

        def _on_action(result) -> None:
            if result is None:
                return
            if result.action == "reset-hard":
                self.push_screen(ConfirmModal(
                    "Hard Reset — irreversible",
                    f"Reset HEAD to [cyan]{result.sha[:7]}[/cyan] and discard\n"
                    f"all working directory changes?",
                    confirm_label="Reset Hard",
                    danger=True,
                ), callback=lambda confirmed: confirmed and _execute(result))
            else:
                _execute(result)

        self.push_screen(CommitActionsModal(commit, is_head), callback=_on_action)

    # ── File selection ────────────────────────────────────────────────────────

    @on(FileList.FileSelected)
    def _on_file_selected(self, event: FileList.FileSelected):
        if not self._current_repo:
            return
        self._current_file_staged = event.staged
        diff = self._current_repo.get_diff(event.fs.path, staged=event.staged)
        dv = self.query_one("#diff-view", DiffView)
        dv.show_diff(diff, event.fs.path)
        # Switch to diff tab
        self.query_one("#right-tabs", TabbedContent).active = "tab-diff"

    # ── Stage / unstage ───────────────────────────────────────────────────────

    @on(FileList.StageToggled)
    def _on_stage_toggled(self, event: FileList.StageToggled):
        if not self._current_repo:
            return
        if event.currently_staged:
            ok, err = self._current_repo.unstage_file(event.fs.path)
        else:
            ok, err = self._current_repo.stage_file(event.fs.path)
        if not ok:
            self.notify(err, title="Stage error", severity="error")
        self._refresh_current_repo()

    @on(DiffView.HunkStageRequest)
    def _on_hunk_stage(self, event: DiffView.HunkStageRequest):
        if not self._current_repo:
            return
        patch = event.hunk.to_patch(event.file_diff.file_header)
        ok, err = self._current_repo.apply_hunk_patch(patch)
        if ok:
            self.notify(f"Hunk staged ✓", title="Stage hunk")
        else:
            self.notify(err or "Failed to stage hunk", title="Stage hunk", severity="error")
        self._refresh_current_repo()

    # ── Stage / unstage all + discard (App-level so priority=True works) ──────

    def action_stage_all(self):
        if not self._current_repo:
            return
        ok, err = self._current_repo.stage_all()
        if not ok:
            self.notify(err, title="Stage all error", severity="error")
        self._refresh_current_repo()

    def action_unstage_all(self):
        if not self._current_repo:
            return
        ok, err = self._current_repo.unstage_all()
        if not ok:
            self.notify(err, title="Unstage all error", severity="error")
        self._refresh_current_repo()

    def action_discard(self):
        file_list = self.query_one("#file-list", FileList)
        fs = file_list.get_discard_candidate()
        if fs is None:
            return

        def _on_confirm(confirmed: bool) -> None:
            if confirmed:
                file_list.action_discard()
                self._refresh_current_repo()

        self.push_screen(ConfirmModal(
            "Discard changes",
            f"Discard all unstaged changes in [cyan]{fs.path}[/cyan]?\nThis cannot be undone.",
            confirm_label="Discard",
            danger=True,
        ), callback=_on_confirm)

    def action_toggle_stage(self):
        self.query_one("#file-list", FileList).action_toggle_stage()

    def action_toggle_hunk_mode(self):
        self.query_one("#diff-view", DiffView).action_toggle_hunk_mode()

    def action_stage_hunk(self):
        self.query_one("#diff-view", DiffView).action_stage_hunk()

    def action_scroll_down(self):
        self.query_one("#diff-view", DiffView).action_scroll_down()

    def action_scroll_up(self):
        self.query_one("#diff-view", DiffView).action_scroll_up()

    def action_scroll_home(self):
        self.query_one("#diff-view", DiffView).action_scroll_home()

    def action_scroll_end(self):
        self.query_one("#diff-view", DiffView).action_scroll_end()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_refresh(self):
        self.notify("Refreshing…", timeout=1)
        self.refresh_all()
        if self._current_repo:
            self._refresh_current_repo()

    def action_commit(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning")
            return
        status = self._current_repo.get_status()
        if not status.staged_files:
            self.notify("Nothing staged. Stage files first.", severity="warning")
            return
        repo = self._current_repo
        summary = f"({len(status.staged_files)} file(s) staged)"

        def _on_commit(msg: str | None) -> None:
            if msg:
                ok, out = repo.commit(msg)
                if ok:
                    self.notify(out.splitlines()[0] if out else "Committed", title="Commit ✓")
                else:
                    self.notify(out, title="Commit failed", severity="error")
                self._refresh_current_repo()

        self.push_screen(CommitModal(summary), callback=_on_commit)

    @work(thread=True)
    def _do_pull(self, repo: GitRepo):
        ok, out = repo.pull()
        self.call_from_thread(
            self.notify, out.splitlines()[0] if out else ("done" if ok else "failed"),
            title=f"Pull {'✓' if ok else '✗'} {repo.path.name}",
            severity="information" if ok else "error",
        )
        self.call_from_thread(self._refresh_current_repo)

    @work(thread=True)
    def _do_push(self, repo: GitRepo):
        ok, out = repo.push()
        self.call_from_thread(
            self.notify, out.splitlines()[0] if out else ("done" if ok else "failed"),
            title=f"Push {'✓' if ok else '✗'} {repo.path.name}",
            severity="information" if ok else "error",
        )
        self.call_from_thread(self._refresh_current_repo)

    @work(thread=True)
    def _do_fetch(self, repo: GitRepo):
        ok, out = repo.fetch()
        self.call_from_thread(
            self.notify, out.splitlines()[0] if out else ("done" if ok else "failed"),
            title=f"Fetch {'✓' if ok else '✗'} {repo.path.name}",
            severity="information" if ok else "error",
        )
        self.call_from_thread(self._refresh_current_repo)

    def action_pull(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning"); return
        self._do_pull(self._current_repo)

    def action_push(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning"); return
        self._do_push(self._current_repo)

    def action_fetch(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning"); return
        self._do_fetch(self._current_repo)

    def action_force_push(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning"); return
        repo = self._current_repo

        def _on_confirm(confirmed: bool) -> None:
            if confirmed:
                self._do_force_push(repo)

        self.push_screen(ConfirmModal(
            "Force Push",
            f"Force-push [cyan]{repo.path.name}[/cyan] with --force-with-lease?\n"
            f"This overwrites the remote branch.",
            confirm_label="Force Push",
            danger=True,
        ), callback=_on_confirm)

    @work(thread=True)
    def _do_force_push(self, repo: GitRepo):
        ok, out = repo.force_push()
        self.call_from_thread(
            self.notify, out.splitlines()[0] if out else ("done" if ok else "failed"),
            title=f"Force Push {'✓' if ok else '✗'} {repo.path.name}",
            severity="information" if ok else "error",
        )
        self.call_from_thread(self._refresh_current_repo)

    # ── Bulk ops ──────────────────────────────────────────────────────────────

    def _bulk_targets(self) -> list[Path]:
        """Checked repos; fall back to all repos if none checked."""
        sel = self.query_one("#repo-list", RepoList).get_selected_paths()
        return sel if sel else self.query_one("#repo-list", RepoList).get_all_paths()

    def _run_bulk(self, op: str):
        targets = self._bulk_targets()
        if not targets:
            self.notify("No repos loaded", severity="warning")
            return
        self.push_screen(BulkProgressModal(op, targets),
                         callback=lambda _: self.refresh_all())

    def action_bulk_pull(self):
        self._run_bulk("pull")

    def action_bulk_push(self):
        self._run_bulk("push")

    def action_bulk_fetch(self):
        self._run_bulk("fetch")

    def action_select_all(self):
        rl = self.query_one("#repo-list", RepoList)
        all_paths = rl.get_all_paths()
        checked = rl.get_selected_paths()
        rl.select_all(len(checked) < len(all_paths))

    # ── Branch ────────────────────────────────────────────────────────────────

    def action_branch(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning")
            return
        repo = self._current_repo
        branches = repo.list_branches()
        current = repo.get_branch()

        def _on_branch(result: str | None) -> None:
            if result is None:
                return
            if result.startswith("__new__"):
                ok, err = repo.checkout_new_branch(result[7:])
            else:
                ok, err = repo.checkout(result)
            if ok:
                branch_name = result[7:] if result.startswith("__new__") else result
                self.notify(f"Switched to {branch_name}", title="Branch")
            else:
                self.notify(err, title="Branch error", severity="error")
            self._refresh_current_repo()

        self.push_screen(BranchModal(branches, current), callback=_on_branch)

    # ── Stash ─────────────────────────────────────────────────────────────────

    def action_stash(self):
        if not self._current_repo:
            return
        ok, err = self._current_repo.stash()
        if ok:
            self.notify("Stashed changes", title="Stash ✓")
        else:
            self.notify(err or "Nothing to stash", title="Stash", severity="warning")
        self._refresh_current_repo()

    # ── Repo management ───────────────────────────────────────────────────────

    def action_new_repo(self):
        def _on_new_repo(result) -> None:
            if result is None:
                return
            repo, init_msg = GitRepo.init(result.path, initial_branch=result.branch)
            self.notify(init_msg.splitlines()[0] if init_msg else f"Initialized {result.path.name}",
                        title="git init ✓")
            if result.initial_commit:
                repo.stage_all()
                ok, out = repo.commit(result.commit_message)
                if ok:
                    self.notify(out.splitlines()[0] if out else "Committed",
                                title="Initial commit ✓")
                else:
                    self.notify(out, title="Commit failed", severity="error")
            self.config.add_repo(result.path)
            self.refresh_all()

        self.push_screen(NewRepoModal(), callback=_on_new_repo)

    def action_add_repo(self):
        def _on_add_repo(path) -> None:
            if path:
                if self.config.add_repo(path):
                    self.notify(f"Added {path.name}", title="Repo added")
                    self.refresh_all()
                else:
                    self.notify("Already tracked", severity="warning")

        self.push_screen(AddRepoModal(), callback=_on_add_repo)

    def action_clone_repo(self):
        def _on_clone(result) -> None:
            if result is None:
                return
            self.notify(f"Cloning {result.url} …", title="Clone", timeout=60)
            self._do_clone(result.url, result.dest)

        self.push_screen(CloneModal(), callback=_on_clone)

    @work(thread=True)
    def _do_clone(self, url: str, dest: Path):
        try:
            repo, msg = GitRepo.clone(url, dest)
            self.config.add_repo(dest)
            first = msg.splitlines()[-1] if msg else f"Cloned into {dest.name}"
            self.call_from_thread(self.notify, first, title="Clone ✓")
            self.call_from_thread(self.refresh_all)
        except RuntimeError as e:
            first = str(e).splitlines()[0]
            self.call_from_thread(self.notify, first, title="Clone failed", severity="error")

    def action_remotes(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning")
            return
        repo = self._current_repo
        remotes = repo.list_remotes()

        def _on_remote(result) -> None:
            if result is None:
                return
            if result.action == "add":
                ok, err = repo.add_remote(result.name, result.url)
            elif result.action == "set-url":
                ok, err = repo.set_remote_url(result.name, result.url)
            elif result.action == "remove":
                ok, err = repo.remove_remote(result.name)
            else:
                return
            if ok:
                self.notify(f"{result.action} remote '{result.name}'", title="Remotes ✓")
            else:
                self.notify(err, title="Remotes error", severity="error")

        self.push_screen(RemoteModal(remotes), callback=_on_remote)

    def action_remove_repo(self):
        if not self._current_repo:
            self.notify("No repo selected", severity="warning"); return
        path = self._current_repo.path

        def _on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            if self.config.remove_repo(path):
                self._current_repo = None
                self.query_one("#file-list", FileList).clear()
                self.query_one("#diff-view", DiffView).clear()
                self.query_one("#graph-view", GraphView).clear()
                self.refresh_all()
                self.notify(f"Removed {path.name}", title="Repo removed")

        self.push_screen(ConfirmModal(
            "Remove repository",
            f"Remove [cyan]{path.name}[/cyan] from the tracked list?\n(The directory itself is not deleted)",
            confirm_label="Remove",
            danger=False,
        ), callback=_on_confirm)
