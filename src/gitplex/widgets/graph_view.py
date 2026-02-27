"""GraphView — commit graph and log panel."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog, DataTable, TabbedContent, TabPane
from textual.containers import Vertical

from ..git.repo import CommitInfo


_GRAPH_COLOURS = ["cyan", "magenta", "yellow", "green", "blue", "red"]

def _colour_graph_line(line: str) -> str:
    """Add colour to ASCII graph symbols."""
    result = []
    colour_idx = 0
    for ch in line:
        if ch in "*|/\\_":
            c = _GRAPH_COLOURS[colour_idx % len(_GRAPH_COLOURS)]
            result.append(f"[{c}]{ch}[/{c}]")
            if ch == "*":
                colour_idx += 1
        elif ch == "(":
            result.append("[bold yellow](")
        elif ch == ")":
            result.append(")[/bold yellow]")
        else:
            result.append(ch)
    return "".join(result)


class GraphView(Widget):
    """Shows git log --graph and a structured commit table."""

    BORDER_TITLE = "GRAPH"
    BINDINGS = [
        ("j", "scroll_down", "↓"),
        ("k", "scroll_up",   "↑"),
        ("g", "scroll_home", "Top"),
        ("G", "scroll_end",  "Bottom"),
    ]

    DEFAULT_CSS = """
    GraphView {
        border: round $primary;
        height: 1fr;
    }
    GraphView TabbedContent { height: 1fr; }
    GraphView ContentSwitcher { height: 1fr; }
    GraphView TabPane { height: 1fr; }
    GraphView #graph-log { height: 1fr; }
    GraphView #commit-table { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(id="graph-tabs"):
            with TabPane("Graph", id="tab-graph"):
                yield RichLog(id="graph-log", highlight=False, markup=True,
                              wrap=False, auto_scroll=False)
            with TabPane("Log", id="tab-log"):
                tbl = DataTable(id="commit-table", zebra_stripes=True)
                tbl.add_columns("SHA", "Author", "Date", "Subject", "Refs")
                yield tbl

    # ── Public API ────────────────────────────────────────────────────────────

    def show_graph(self, graph_text: str, commits: list[CommitInfo]):
        # Graph tab
        log = self.query_one("#graph-log", RichLog)
        log.clear()
        if graph_text.strip():
            for line in graph_text.splitlines():
                log.write(_colour_graph_line(line))
        else:
            log.write("[dim]No commits.[/dim]")

        # Log table tab
        tbl = self.query_one("#commit-table", DataTable)
        tbl.clear()
        for c in commits:
            refs_label = f"[yellow]{c.refs}[/yellow]" if c.refs else ""
            tbl.add_row(
                f"[cyan]{c.short_sha}[/cyan]",
                c.author[:16],
                c.date[:12],
                c.subject[:55],
                refs_label,
                key=c.sha,
            )

    def clear(self):
        self.query_one("#graph-log", RichLog).clear()
        self.query_one("#commit-table", DataTable).clear()

    # ── Scroll ────────────────────────────────────────────────────────────────

    def action_scroll_down(self):
        self.query_one("#graph-log", RichLog).scroll_down()

    def action_scroll_up(self):
        self.query_one("#graph-log", RichLog).scroll_up()

    def action_scroll_home(self):
        self.query_one("#graph-log", RichLog).scroll_home()

    def action_scroll_end(self):
        self.query_one("#graph-log", RichLog).scroll_end()
