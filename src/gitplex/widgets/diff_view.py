"""DiffView — right panel: colorised diff with hunk-level staging."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import RichLog, Label, ListView, ListItem
from textual.containers import Vertical
from textual import on

from ..git.diff import FileDiff, Hunk, parse_diff, render_diff_rich


class HunkItem(ListItem):
    DEFAULT_CSS = """
    HunkItem { height: 1; padding: 0 1; }
    HunkItem.selected-hunk { background: $accent 30%; }
    """

    def __init__(self, hunk: Hunk, idx: int, file_diff: FileDiff):
        super().__init__()
        self.hunk = hunk
        self.idx = idx
        self.file_diff = file_diff

    def compose(self) -> ComposeResult:
        yield Label(
            f"  Hunk {self.idx + 1}: {self.hunk.header.strip()[:60]}  "
            f"[+{self.hunk.added_count} -{self.hunk.removed_count}]"
        )


class DiffView(Widget):
    """Shows diff for the currently selected file.

    In hunk mode (toggle with 'h') shows each hunk separately
    and lets you stage individual hunks with 's'.
    """

    class HunkStageRequest(Message):
        def __init__(self, file_diff: FileDiff, hunk: Hunk):
            super().__init__()
            self.file_diff = file_diff
            self.hunk = hunk

    BORDER_TITLE = "DIFF"
    BINDINGS = []

    DEFAULT_CSS = """
    DiffView {
        border: round $primary;
        height: 1fr;
    }
    DiffView #diff-log  { height: 1fr; display: block; }
    DiffView #hunk-list { height: 1fr; display: none; }
    DiffView #hunk-body { height: 3fr; display: none; }
    DiffView.hunk-mode #diff-log  { display: none; }
    DiffView.hunk-mode #hunk-list { display: block; }
    DiffView.hunk-mode #hunk-body { display: block; }
    DiffView #diff-hint {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._file_diff: FileDiff | None = None
        self._diff_text: str = ""
        self._hunk_mode: bool = False

    def compose(self) -> ComposeResult:
        yield Label("  [h] toggle hunk mode  [s] stage hunk  [j/k] scroll",
                    id="diff-hint", markup=True)
        yield RichLog(id="diff-log", highlight=False, markup=True,
                      wrap=False, auto_scroll=False)
        yield ListView(id="hunk-list")
        yield RichLog(id="hunk-body", highlight=False, markup=True,
                      wrap=False, auto_scroll=False)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_diff(self, diff_text: str, file_path: str = ""):
        """Display raw diff text (plain, no hunk mode)."""
        self._diff_text = diff_text
        parsed = parse_diff(diff_text)
        self._file_diff = parsed[0] if parsed else None

        log = self.query_one("#diff-log", RichLog)
        log.clear()
        if diff_text.strip():
            log.write(render_diff_rich(diff_text))
        else:
            log.write("[dim]No changes.[/dim]")

        if self._hunk_mode:
            self._populate_hunk_list()
        self.border_title = f"DIFF  {file_path}"

    def clear(self):
        self._diff_text = ""
        self._file_diff = None
        self.query_one("#diff-log", RichLog).clear()
        self.query_one("#hunk-list", ListView).clear()
        self.query_one("#hunk-body", RichLog).clear()
        self.border_title = "DIFF"

    # ── Hunk mode ─────────────────────────────────────────────────────────────

    def action_toggle_hunk_mode(self):
        self._hunk_mode = not self._hunk_mode
        if self._hunk_mode:
            self.add_class("hunk-mode")
            self._populate_hunk_list()
        else:
            self.remove_class("hunk-mode")

    def _populate_hunk_list(self):
        lv = self.query_one("#hunk-list", ListView)
        lv.clear()
        if self._file_diff:
            for i, hunk in enumerate(self._file_diff.hunks):
                lv.append(HunkItem(hunk, i, self._file_diff))

    @on(ListView.Highlighted)
    def _on_hunk_highlighted(self, event: ListView.Highlighted):
        event.stop()
        item = event.item
        if isinstance(item, HunkItem):
            body = self.query_one("#hunk-body", RichLog)
            body.clear()
            hunk_text = item.hunk.header + "\n"
            hunk_text += "\n".join(l.content for l in item.hunk.lines)
            body.write(render_diff_rich(hunk_text))

    def action_stage_hunk(self):
        if not self._hunk_mode or not self._file_diff:
            return
        lv = self.query_one("#hunk-list", ListView)
        idx = lv.index
        if idx is None:
            return
        hunks = self._file_diff.hunks
        if 0 <= idx < len(hunks):
            self.post_message(self.HunkStageRequest(self._file_diff, hunks[idx]))

    # ── Scroll actions ────────────────────────────────────────────────────────

    def action_scroll_down(self):
        self.query_one("#diff-log", RichLog).scroll_down()

    def action_scroll_up(self):
        self.query_one("#diff-log", RichLog).scroll_up()

    def action_scroll_home(self):
        self.query_one("#diff-log", RichLog).scroll_home()

    def action_scroll_end(self):
        self.query_one("#diff-log", RichLog).scroll_end()
