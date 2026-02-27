"""FileList — middle panel: staged / unstaged files with toggle staging."""
from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label, TabbedContent, TabPane
from textual.containers import Horizontal
from textual import on

from ..git.repo import FileStatus, GitRepo


# ── status colours ────────────────────────────────────────────────────────────
_STATUS_COLOUR = {
    "M": "yellow", "A": "green", "D": "red",
    "R": "cyan",   "C": "cyan",  "?": "dim",
    " ": "white",
}

def _coloured(ch: str) -> str:
    c = _STATUS_COLOUR.get(ch.upper(), "white")
    return f"[{c}]{ch}[/{c}]"


class FileItem(ListItem):
    DEFAULT_CSS = """
    FileItem { height: 1; padding: 0 1; }
    FileItem > Horizontal { height: 1; }
    FileItem .file-status { width: 3; }
    FileItem .file-path   { width: 1fr; }
    """

    def __init__(self, fs: FileStatus, is_staged_panel: bool):
        super().__init__()
        self.fs = fs
        self.is_staged_panel = is_staged_panel

    def compose(self) -> ComposeResult:
        st = self.fs.staged if self.is_staged_panel else self.fs.unstaged
        if self.fs.is_untracked:
            st = "?"
        with Horizontal():
            yield Label(_coloured(st), classes="file-status", markup=True)
            yield Label(self.fs.path, classes="file-path")


class FileList(Widget):
    """Staged / Unstaged tabs with file lists."""

    class FileSelected(Message):
        def __init__(self, fs: FileStatus, staged: bool):
            super().__init__()
            self.fs = fs
            self.staged = staged

    class StageToggled(Message):
        def __init__(self, fs: FileStatus, currently_staged: bool):
            super().__init__()
            self.fs = fs
            self.currently_staged = currently_staged

    BORDER_TITLE = "FILES"
    BINDINGS = []

    DEFAULT_CSS = """
    FileList {
        border: round $primary;
        height: 1fr;
        min-height: 6;
    }
    FileList TabbedContent { height: 1fr; }
    FileList ContentSwitcher { height: 1fr; }
    FileList TabPane { height: 1fr; }
    FileList ListView  { height: 1fr; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._staged: list[FileStatus] = []
        self._unstaged: list[FileStatus] = []
        self._repo_path: Path | None = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="file-tabs"):
            with TabPane("Unstaged", id="tab-unstaged"):
                yield ListView(id="lv-unstaged")
            with TabPane("Staged", id="tab-staged"):
                yield ListView(id="lv-staged")

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, staged: list[FileStatus], unstaged: list[FileStatus], repo_path: Path):
        self._staged = staged
        self._unstaged = unstaged
        self._repo_path = repo_path
        self._reload_lists()

    def clear(self):
        self._staged = []
        self._unstaged = []
        self._reload_lists()

    def _reload_lists(self):
        lv_u = self.query_one("#lv-unstaged", ListView)
        lv_s = self.query_one("#lv-staged", ListView)
        lv_u.clear()
        lv_s.clear()
        for f in self._unstaged:
            lv_u.append(FileItem(f, is_staged_panel=False))
        for f in self._staged:
            lv_s.append(FileItem(f, is_staged_panel=True))

    def _active_list(self) -> tuple[ListView, bool]:
        tabs = self.query_one(TabbedContent)
        is_staged = tabs.active == "tab-staged"
        lv_id = "#lv-staged" if is_staged else "#lv-unstaged"
        return self.query_one(lv_id, ListView), is_staged

    def _selected_item(self) -> tuple[FileItem | None, bool]:
        lv, is_staged = self._active_list()
        if lv.highlighted_child is not None:
            idx = lv.index
            if idx is not None:
                items = list(lv.query(FileItem))
                if 0 <= idx < len(items):
                    return items[idx], is_staged
        return None, is_staged

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_stage(self):
        item, is_staged = self._selected_item()
        if item:
            self.post_message(self.StageToggled(item.fs, is_staged))

    def action_stage_all(self):
        if self._repo_path:
            repo = GitRepo(self._repo_path)
            repo.stage_all()

    def action_unstage_all(self):
        if self._repo_path:
            repo = GitRepo(self._repo_path)
            repo.unstage_all()

    def action_discard(self):
        item, is_staged = self._selected_item()
        if item and not is_staged and self._repo_path:
            repo = GitRepo(self._repo_path)
            repo.discard_file(item.fs.path)

    # ── Events ────────────────────────────────────────────────────────────────

    @on(ListView.Selected)
    def _on_item_selected(self, event: ListView.Selected):
        event.stop()
        item = event.item
        if isinstance(item, FileItem):
            lv, is_staged = self._active_list()
            self.post_message(self.FileSelected(item.fs, is_staged))
