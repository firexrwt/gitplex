"""Unified diff parser — splits diffs into files, hunks and lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


LineType = Literal["+", "-", " ", "@", "h"]


@dataclass
class DiffLine:
    content: str          # raw line text (no newline)
    kind: LineType        # +, -, context, hunk header, file header


@dataclass
class Hunk:
    header: str           # '@@ -a,b +c,d @@ optional context'
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine] = field(default_factory=list)

    def to_patch(self, file_header: str) -> str:
        """Return a minimal patch string for this hunk (for git apply --cached)."""
        body = "\n".join(l.content for l in self.lines)
        # ensure trailing newline
        if not body.endswith("\n"):
            body += "\n"
        return f"{file_header}{self.header}\n{body}"

    @property
    def added_count(self) -> int:
        return sum(1 for l in self.lines if l.kind == "+")

    @property
    def removed_count(self) -> int:
        return sum(1 for l in self.lines if l.kind == "-")

    @property
    def display_header(self) -> str:
        m = re.match(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(.*)", self.header)
        ctx = m.group(1).strip() if m else ""
        summary = f"+{self.added_count} -{self.removed_count}"
        return f"{self.header.split('@@')[1].strip()[:40]}  [{summary}]" if ctx else f"[{summary}]"


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    hunks: list[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    file_header: str = ""   # everything before first @@

    @property
    def path(self) -> str:
        return self.new_path or self.old_path

    @property
    def total_added(self) -> int:
        return sum(h.added_count for h in self.hunks)

    @property
    def total_removed(self) -> int:
        return sum(h.removed_count for h in self.hunks)


# ── Parser ────────────────────────────────────────────────────────────────────

_DIFF_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK_HEADER = re.compile(r"^(@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*)")


def parse_diff(text: str) -> list[FileDiff]:
    """Parse unified diff text into a list of FileDiff objects."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    hunk: Hunk | None = None
    header_lines: list[str] = []

    def _flush_hunk():
        nonlocal hunk
        if current and hunk:
            current.hunks.append(hunk)
            hunk = None

    def _flush_file():
        _flush_hunk()
        if current:
            files.append(current)

    for raw in text.splitlines(keepends=False):
        m = _DIFF_HEADER.match(raw)
        if m:
            _flush_file()
            current = FileDiff(old_path=m.group(1), new_path=m.group(2),
                               file_header=raw + "\n")
            hunk = None
            header_lines = [raw]
            continue

        if current is None:
            continue

        # Accumulate file header until first @@
        if not current.hunks and hunk is None:
            if raw.startswith("new file"):
                current.is_new = True
            elif raw.startswith("deleted file"):
                current.is_deleted = True
            elif raw.startswith("Binary"):
                current.is_binary = True
            current.file_header += raw + "\n"

        mh = _HUNK_HEADER.match(raw)
        if mh:
            _flush_hunk()
            hunk = Hunk(
                header=mh.group(1),
                old_start=int(mh.group(2)),
                old_count=int(mh.group(3) or 1),
                new_start=int(mh.group(4)),
                new_count=int(mh.group(5) or 1),
            )
            continue

        if hunk is not None:
            if raw.startswith("+"):
                hunk.lines.append(DiffLine(raw, "+"))
            elif raw.startswith("-"):
                hunk.lines.append(DiffLine(raw, "-"))
            elif raw.startswith(" ") or raw == "":
                hunk.lines.append(DiffLine(raw, " "))
            elif raw.startswith("\\"):
                hunk.lines.append(DiffLine(raw, " "))  # "\ No newline at end"

    _flush_file()
    return files


def render_diff_rich(diff_text: str) -> str:
    """Return Rich-markup string for colourised diff display."""
    lines = []
    for raw in diff_text.splitlines():
        if raw.startswith("+++") or raw.startswith("---"):
            lines.append(f"[bold]{raw}[/bold]")
        elif raw.startswith("@@"):
            lines.append(f"[bold cyan]{raw}[/bold cyan]")
        elif raw.startswith("+"):
            lines.append(f"[green]{raw}[/green]")
        elif raw.startswith("-"):
            lines.append(f"[red]{raw}[/red]")
        elif raw.startswith("diff ") or raw.startswith("index "):
            lines.append(f"[dim]{raw}[/dim]")
        else:
            lines.append(raw)
    return "\n".join(lines)
