"""RepoList — left panel showing all tracked repositories with live status."""
from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label, Checkbox
from textual.containers import Horizontal
from textual import on

from ..git.repo import GitRepo, RepoStatus


class RepoItem(ListItem):
    """A single repo entry: checkbox + name + branch + ahead/behind badge."""

    DEFAULT_CSS = """
    RepoItem {
        height: 3;
        padding: 0 1;
    }
    RepoItem > Horizontal {
        height: 3;
        align: left middle;
    }
    RepoItem .repo-name { width: 1fr; }
    RepoItem .repo-branch { color: $accent; width: 16; }
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
        ahead  = f" ↑{s.ahead}"  if s.ahead  else "    "
        behind = f" ↓{s.behind}" if s.behind else "    "
        dirty  = " ●" if s.is_dirty else "  "

        with Horizontal():
            yield Checkbox(value=self._checked, id=f"chk-{id(self)}")
            yield Label(s.name[:22], classes="repo-name")
            yield Label(s.branch[:14], classes="repo-branch")
            yield Label(ahead,  classes="badge-ahead")
            yield Label(behind, classes="badge-behind")
            yield Label(dirty,  classes="badge-dirty")

    def refresh_status(self, status: RepoStatus):
        self.repo_status = status
        s = status
        self.query_one(".repo-name", Label).update(s.name[:22])
        self.query_one(".repo-branch", Label).update(s.branch[:14])
        self.query_one(".badge-ahead",  Label).update(f" ↑{s.ahead}"  if s.ahead  else "    ")
        self.query_one(".badge-behind", Label).update(f" ↓{s.behind}" if s.behind else "    ")
        self.query_one(".badge-dirty",  Label).update(" ●" if s.is_dirty else "  ")

    @property
    def is_checked(self) -> bool:
        try:
            return self.query_one(Checkbox).value
        except Exception:
            return False


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
            try:
                item.query_one(Checkbox).value = checked
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
