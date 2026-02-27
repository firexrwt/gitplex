"""Modal screens: commit, add-repo, new-repo, branch checkout, bulk-op progress."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button, DataTable, RichLog, Checkbox
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import on


@dataclass
class NewRepoResult:
    path: Path
    branch: str
    initial_commit: bool
    commit_message: str


# ── Commit modal ──────────────────────────────────────────────────────────────

class CommitModal(ModalScreen[str | None]):
    """Commit message dialog. Returns the message string or None."""

    DEFAULT_CSS = """
    CommitModal > Vertical {
        width: 70;
        height: auto;
        max-height: 20;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    CommitModal Label  { margin-bottom: 1; }
    CommitModal Input  { margin-bottom: 1; }
    CommitModal Horizontal { height: auto; align: right middle; }
    CommitModal Button { margin-left: 1; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+enter", "confirm", "Confirm"),
    ]

    def __init__(self, staged_summary: str = ""):
        super().__init__()
        self._staged_summary = staged_summary

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]Commit[/bold]  {self._staged_summary}", markup=True)
            yield Input(placeholder="Commit message…", id="commit-input")
            with Horizontal():
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Commit", variant="primary", id="btn-commit")

    def action_cancel(self):
        self.dismiss(None)

    def action_confirm(self):
        msg = self.query_one("#commit-input", Input).value.strip()
        self.dismiss(msg if msg else None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-commit":
            msg = self.query_one("#commit-input", Input).value.strip()
            self.dismiss(msg if msg else None)


# ── Add-repo modal ────────────────────────────────────────────────────────────

class AddRepoModal(ModalScreen[Path | None]):
    """Ask for a path and return it (validated as git repo) or None."""

    DEFAULT_CSS = """
    AddRepoModal > Vertical {
        width: 70;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    AddRepoModal Label  { margin-bottom: 1; }
    AddRepoModal Input  { margin-bottom: 1; }
    AddRepoModal #error-label { color: $error; height: 1; }
    AddRepoModal Horizontal { height: auto; align: right middle; }
    AddRepoModal Button { margin-left: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Add repository[/bold]", markup=True)
            yield Input(
                placeholder="/path/to/repo  or  . for current dir",
                id="path-input",
            )
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("Cancel",  variant="default", id="btn-cancel")
                yield Button("Add", variant="primary",  id="btn-add")

    def action_cancel(self):
        self.dismiss(None)

    def _try_add(self):
        from ..git.repo import GitRepo
        raw = self.query_one("#path-input", Input).value.strip()
        path = Path(raw).expanduser().resolve()
        err = self.query_one("#error-label", Label)
        if not path.exists():
            err.update(f"Path not found: {path}")
            return
        if not GitRepo.is_git_repo(path):
            err.update("Not a git repository.")
            return
        self.dismiss(path)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-add":
            self._try_add()

    def on_input_submitted(self, _event: Input.Submitted):
        self._try_add()


# ── New-repo modal ────────────────────────────────────────────────────────────

class NewRepoModal(ModalScreen[NewRepoResult | None]):
    """git init — create a brand-new repo or init inside an existing folder."""

    DEFAULT_CSS = """
    NewRepoModal > Vertical {
        width: 72;
        height: auto;
        max-height: 28;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    NewRepoModal Label         { margin-bottom: 1; }
    NewRepoModal Input         { margin-bottom: 1; }
    NewRepoModal #preview      { color: $text-muted; height: 1; margin-bottom: 1; }
    NewRepoModal #preview.warn { color: $warning; }
    NewRepoModal #preview.ok   { color: $success; }
    NewRepoModal #msg-row      { height: auto; display: none; margin-bottom: 1; }
    NewRepoModal #msg-row.show { display: block; }
    NewRepoModal #error-label  { color: $error; height: 1; }
    NewRepoModal Horizontal    { height: auto; align: right middle; margin-top: 1; }
    NewRepoModal Button        { margin-left: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Create / init repository[/bold]", markup=True)
            yield Input(placeholder="/path/to/folder  or  . for current dir",
                        id="path-input")
            yield Label("", id="preview")
            yield Input(placeholder="Initial branch name (default: main)",
                        id="branch-input")
            yield Checkbox("Make initial commit (add all + commit)",
                           value=False, id="chk-init-commit")
            with Vertical(id="msg-row"):
                yield Input(placeholder="Commit message (default: Initial commit)",
                            id="msg-input")
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Create / Init", variant="primary", id="btn-create")

    # ── Live preview while typing path ───────────────────────────────────────

    @on(Input.Changed, "#path-input")
    def _update_preview(self, event: Input.Changed):
        from ..git.repo import GitRepo
        raw = event.value.strip()
        lbl = self.query_one("#preview", Label)
        if not raw:
            lbl.update("")
            lbl.remove_class("warn", "ok")
            return
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            lbl.update(f"  New directory will be created: {path}")
            lbl.remove_class("warn")
            lbl.add_class("ok")
        elif GitRepo.is_git_repo(path):
            lbl.update(f"  ⚠ Already a git repo!")
            lbl.add_class("warn"); lbl.remove_class("ok")
        else:
            n = sum(1 for _ in path.iterdir()) if path.is_dir() else 0
            lbl.update(f"  Existing folder — {n} item(s) found, will be tracked")
            lbl.remove_class("warn")
            lbl.add_class("ok")

    @on(Checkbox.Changed, "#chk-init-commit")
    def _toggle_msg_row(self, event: Checkbox.Changed):
        row = self.query_one("#msg-row")
        if event.value:
            row.add_class("show")
        else:
            row.remove_class("show")

    # ── Submit ────────────────────────────────────────────────────────────────

    def action_cancel(self):
        self.dismiss(None)

    def _try_create(self):
        from ..git.repo import GitRepo
        raw = self.query_one("#path-input", Input).value.strip()
        err = self.query_one("#error-label", Label)
        if not raw:
            err.update("Path is required.")
            return
        path = Path(raw).expanduser().resolve()
        if GitRepo.is_git_repo(path):
            err.update("Already a git repo — use 'Add repo' instead.")
            return
        branch = self.query_one("#branch-input", Input).value.strip() or "main"
        do_commit = self.query_one("#chk-init-commit", Checkbox).value
        msg = self.query_one("#msg-input", Input).value.strip() or "Initial commit"
        self.dismiss(NewRepoResult(
            path=path, branch=branch,
            initial_commit=do_commit, commit_message=msg,
        ))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-create":
            self._try_create()

    def on_input_submitted(self, _: Input.Submitted):
        self._try_create()


# ── Bulk-op progress modal ────────────────────────────────────────────────────

class BulkProgressModal(ModalScreen[None]):
    """Show a live log of bulk git operations (pull/push/fetch)."""

    DEFAULT_CSS = """
    BulkProgressModal > Vertical {
        width: 80;
        height: 30;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    BulkProgressModal #bulk-log { height: 1fr; border: round $primary; }
    BulkProgressModal Button { margin-top: 1; align-horizontal: right; }
    """

    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, operation: str, repos: list[Path]):
        super().__init__()
        self._operation = operation
        self._repos = repos

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self._operation.upper()}[/bold] — {len(self._repos)} repos",
                        markup=True)
            yield RichLog(id="bulk-log", highlight=False, markup=True)
            yield Button("Close", variant="primary", id="btn-close", disabled=True)

    def on_mount(self):
        self.run_worker(self._run_bulk(), exclusive=True)

    async def _run_bulk(self):
        from ..git.repo import GitRepo
        import asyncio

        log = self.query_one("#bulk-log", RichLog)
        semaphore = asyncio.Semaphore(4)  # max 4 concurrent ops

        async def do_one(path: Path):
            async with semaphore:
                repo = GitRepo(path)
                log.write(f"[cyan]→ {path.name}[/cyan] …")
                ok, out = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: getattr(repo, self._operation)(),
                )
                if ok:
                    first_line = out.splitlines()[0] if out else "done"
                    log.write(f"[green]✓ {path.name}[/green]  {first_line}")
                else:
                    first_line = out.splitlines()[0] if out else "failed"
                    log.write(f"[red]✗ {path.name}[/red]  {first_line}")

        await asyncio.gather(*(do_one(p) for p in self._repos))
        log.write("\n[bold green]Done.[/bold green]")
        self.query_one("#btn-close", Button).disabled = False

    def action_close(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-close":
            self.dismiss(None)


# ── Clone modal ───────────────────────────────────────────────────────────────

@dataclass
class CloneResult:
    url: str
    dest: Path


class CloneModal(ModalScreen[CloneResult | None]):
    """Clone a remote repository to a local path."""

    DEFAULT_CSS = """
    CloneModal > Vertical {
        width: 72;
        height: auto;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    CloneModal Label         { margin-bottom: 1; }
    CloneModal Input         { margin-bottom: 1; }
    CloneModal #dest-preview { color: $text-muted; height: 1; margin-bottom: 1; }
    CloneModal #error-label  { color: $error; height: 1; }
    CloneModal Horizontal    { height: auto; align: right middle; margin-top: 1; }
    CloneModal Button        { margin-left: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Clone remote repository[/bold]", markup=True)
            yield Input(placeholder="https://github.com/user/repo.git  or  git@github.com:user/repo.git",
                        id="url-input")
            yield Input(placeholder="Local destination (default: ~/  + repo name)",
                        id="dest-input")
            yield Label("", id="dest-preview")
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Clone",  variant="primary",  id="btn-clone")

    @on(Input.Changed, "#url-input")
    def _update_dest_hint(self, event: Input.Changed):
        url = event.value.strip()
        preview = self.query_one("#dest-preview", Label)
        if not url:
            preview.update("")
            return
        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        suggested = Path.home() / name
        dest_val = self.query_one("#dest-input", Input).value.strip()
        if not dest_val:
            preview.update(f"  Will clone into: {suggested}")

    def action_cancel(self):
        self.dismiss(None)

    def _try_clone(self):
        url = self.query_one("#url-input", Input).value.strip()
        dest_raw = self.query_one("#dest-input", Input).value.strip()
        err = self.query_one("#error-label", Label)
        if not url:
            err.update("URL is required.")
            return
        if dest_raw:
            dest = Path(dest_raw).expanduser().resolve()
        else:
            name = url.rstrip("/").split("/")[-1].removesuffix(".git")
            dest = Path.home() / name
        if dest.exists() and any(dest.iterdir()):
            err.update(f"Destination already exists and is not empty: {dest}")
            return
        self.dismiss(CloneResult(url=url, dest=dest))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-clone":
            self._try_clone()

    def on_input_submitted(self, _: Input.Submitted):
        self._try_clone()


# ── Remote management modal ───────────────────────────────────────────────────

@dataclass
class RemoteResult:
    action: str   # "add" | "set-url" | "remove"
    name: str
    url: str = ""


class RemoteModal(ModalScreen[RemoteResult | None]):
    """View and manage git remotes for the current repository."""

    DEFAULT_CSS = """
    RemoteModal > Vertical {
        width: 72;
        height: auto;
        max-height: 28;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    RemoteModal Label       { margin-bottom: 1; }
    RemoteModal #remote-tbl { height: 6; border: round $primary; margin-bottom: 1; }
    RemoteModal Input       { margin-bottom: 1; }
    RemoteModal #error-label { color: $error; height: 1; }
    RemoteModal Horizontal  { height: auto; align: right middle; margin-top: 1; }
    RemoteModal Button      { margin-left: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, remotes: list[tuple[str, str]]):
        super().__init__()
        self._remotes = remotes

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Remote management[/bold]", markup=True)
            tbl = DataTable(id="remote-tbl", zebra_stripes=True)
            tbl.add_columns("Name", "URL")
            for name, url in self._remotes:
                tbl.add_row(name, url, key=name)
            yield tbl
            yield Input(placeholder="Remote name (e.g. origin)", id="name-input")
            yield Input(placeholder="URL  (https://... or git@...)", id="url-input")
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("Cancel",     variant="default", id="btn-cancel")
                yield Button("Add",        variant="primary",  id="btn-add")
                yield Button("Set URL",    variant="warning",  id="btn-set")
                yield Button("Remove",     variant="error",    id="btn-remove")

    def _get_remote_name(self) -> str:
        tbl = self.query_one("#remote-tbl", DataTable)
        inp = self.query_one("#name-input", Input).value.strip()
        if inp:
            return inp
        if tbl.cursor_row is not None and self._remotes:
            return tbl.get_row_at(tbl.cursor_row)[0]
        return ""

    def _get_remote_url(self) -> str:
        return self.query_one("#url-input", Input).value.strip()

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        err = self.query_one("#error-label", Label)
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-add":
            name, url = self._get_remote_name(), self._get_remote_url()
            if not name or not url:
                err.update("Name and URL are both required.")
                return
            self.dismiss(RemoteResult("add", name, url))
        elif event.button.id == "btn-set":
            name, url = self._get_remote_name(), self._get_remote_url()
            if not name or not url:
                err.update("Name and URL are both required.")
                return
            self.dismiss(RemoteResult("set-url", name, url))
        elif event.button.id == "btn-remove":
            name = self._get_remote_name()
            if not name:
                err.update("Select or type a remote name.")
                return
            self.dismiss(RemoteResult("remove", name))


# ── Branch checkout modal ─────────────────────────────────────────────────────

class BranchModal(ModalScreen[str | None]):
    """Show branch list and let user switch / create branch."""

    DEFAULT_CSS = """
    BranchModal > Vertical {
        width: 60;
        height: 25;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    BranchModal #branch-list { height: 1fr; border: round $primary; }
    BranchModal #new-branch-input { margin-top: 1; }
    BranchModal Horizontal { height: auto; align: right middle; margin-top: 1; }
    BranchModal Button { margin-left: 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, branches: list[str], current: str):
        super().__init__()
        self._branches = branches
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]Branches[/bold]  (current: [cyan]{self._current}[/cyan])",
                        markup=True)
            tbl = DataTable(id="branch-list", zebra_stripes=True)
            tbl.add_column("Branch")
            for b in self._branches:
                marker = "● " if b == self._current else "  "
                tbl.add_row(f"{marker}{b}", key=b)
            yield tbl
            yield Input(placeholder="New branch name (optional)…",
                        id="new-branch-input")
            with Horizontal():
                yield Button("Cancel",   variant="default", id="btn-cancel")
                yield Button("Checkout", variant="primary", id="btn-checkout")
                yield Button("New",      variant="success", id="btn-new")

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-checkout":
            tbl = self.query_one("#branch-list", DataTable)
            if tbl.cursor_row is not None:
                key = tbl.get_row_at(tbl.cursor_row)[0].plain.strip().lstrip("● ")
                self.dismiss(key)
        elif event.button.id == "btn-new":
            name = self.query_one("#new-branch-input", Input).value.strip()
            self.dismiss(f"__new__{name}" if name else None)
