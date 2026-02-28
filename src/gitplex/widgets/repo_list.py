"""RepoList — left panel showing all tracked repositories with live status."""
from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.events import Click
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label
from textual.containers import Horizontal, Vertical
from textual import on

from ..git.repo import GitRepo, RepoStatus


class RepoItem(ListItem):
    """A single repo entry: checkbox + name + branch + ahead/behind badge."""

    DEFAULT_CSS = """
    RepoItem {
        height: 2;
        padding: 0 1;
    }
    RepoItem > Vertical   { height: 2; }
    RepoItem .row-name    { height: 1; }
    RepoItem .row-info    { height: 1; }
    RepoItem .chk-label   { width: 3; }
    RepoItem .repo-name   { width: 1fr; }
    RepoItem .chk-spacer  { width: 3; }
    RepoItem .repo-branch { color: $accent; width: 1fr; }
    RepoItem .badge-ahead  { color: $success; width: 4; }
    RepoItem .badge-behind { color: $warning; width: 4; }
    RepoItem .badge-dirty  { color: $error;   width: 3; }
    """

    def __init__(self, status: RepoStatus, checked: bool = False):
        super().__init__()
        self.repo_status = status
        self._checked = checked

    def compose(self) -> ComposeResult:
        s = self.repo_status
        ahead  = f"↑{s.ahead}"  if s.ahead  else ""
        behind = f"↓{s.behind}" if s.behind else ""
        dirty  = "●" if s.is_dirty else ""
        chk = "☑" if self._checked else "☐"

        with Vertical():
            with Horizontal(classes="row-name"):
                yield Label(chk, classes="chk-label")
                yield Label(s.name, classes="repo-name")
            with Horizontal(classes="row-info"):
                yield Label("   ", classes="chk-spacer")
                yield Label(s.branch, classes="repo-branch")
                yield Label(ahead,  classes="badge-ahead")
                yield Label(behind, classes="badge-behind")
                yield Label(dirty,  classes="badge-dirty")

    def on_click(self, event: Click) -> None:
        # Toggle only when clicking the checkbox label itself
        if event.widget is not None and getattr(event.widget, "has_class", None):
            if event.widget.has_class("chk-label"):
                self._checked = not self._checked
                event.widget.update("☑" if self._checked else "☐")
                event.stop()

    def refresh_status(self, status: RepoStatus):
        self.repo_status = status
        s = status
        ahead  = f"↑{s.ahead}"  if s.ahead  else ""
        behind = f"↓{s.behind}" if s.behind else ""
        dirty  = "●" if s.is_dirty else ""
        self.query_one(".repo-name",   Label).update(s.name)
        self.query_one(".repo-branch", Label).update(s.branch)
        self.query_one(".badge-ahead",  Label).update(ahead)
        self.query_one(".badge-behind", Label).update(behind)
        self.query_one(".badge-dirty",  Label).update(dirty)

    @property
    def is_checked(self) -> bool:
        return self._checked


class RepoList(Widget):
    """Full repo panel: scrollable list + selection state."""

    class RepoSelected(Message):
        def __init__(self, path: Path, status: RepoStatus):
            super().__init__()
            self.path = path
            self.status = status

    BORDER_TITLE = "REPOS"

    DEFAULT_CSS = """
    RepoList {
        border: round $primary;
        height: 1fr;
        min-height: 6;
    }
    RepoList > ListView { height: 1fr; }
    """

    def __init__(self, statuses: list[RepoStatus] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._statuses: list[RepoStatus] = statuses or []

    def compose(self) -> ComposeResult:
        lv = ListView(id="repo-listview")
        for s in self._statuses:
            lv.append(RepoItem(s))
        yield lv

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, statuses: list[RepoStatus]):
        self._statuses = statuses
        lv = self.query_one(ListView)
        lv.clear()
        for s in statuses:
            lv.append(RepoItem(s))

    def update_status(self, path: Path, status: RepoStatus):
        lv = self.query_one(ListView)
        for item in lv.query(RepoItem):
            if item.repo_status.path == path:
                item.refresh_status(status)
                break

    def get_selected_paths(self) -> list[Path]:
        """Return paths of all checked repos (for bulk ops)."""
        lv = self.query_one(ListView)
        return [item.repo_status.path
                for item in lv.query(RepoItem)
                if item.is_checked]

    def get_all_paths(self) -> list[Path]:
        lv = self.query_one(ListView)
        return [item.repo_status.path for item in lv.query(RepoItem)]

    def select_all(self, checked: bool = True):
        for item in self.query(RepoItem):
            item._checked = checked
            try:
                item.query_one(".chk-label", Label).update("☑" if checked else "☐")
            except Exception:
                pass

    # ── Events ────────────────────────────────────────────────────────────────

    @on(ListView.Selected)
    def _on_list_selected(self, event: ListView.Selected):
        event.stop()
        item = event.item
        if isinstance(item, RepoItem):
            self.post_message(self.RepoSelected(
                path=item.repo_status.path,
                status=item.repo_status,
            ))
