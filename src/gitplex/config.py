"""Config — persists repo list and user preferences."""
from __future__ import annotations

import json
from pathlib import Path


_CONFIG_DIR  = Path.home() / ".config" / "gitplex"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_SOURCE_DIR_FILE = _CONFIG_DIR / "source_dir"

_DEFAULTS = {
    "repos": [],
    "auto_fetch_interval": 0,   # seconds, 0 = disabled
    "max_log_entries": 80,
    "last_update_check": 0.0,   # unix timestamp
}


class Config:
    def __init__(self):
        self._data: dict = {}
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self):
        if _CONFIG_FILE.exists():
            try:
                self._data = json.loads(_CONFIG_FILE.read_text())
            except Exception:
                self._data = {}
        for k, v in _DEFAULTS.items():
            self._data.setdefault(k, v)

    def _save(self):
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(self._data, indent=2))

    # ── Repos ─────────────────────────────────────────────────────────────────

    @property
    def repos(self) -> list[Path]:
        return [Path(p) for p in self._data.get("repos", [])]

    def add_repo(self, path: Path) -> bool:
        path = path.resolve()
        paths = [str(p) for p in self.repos]
        if str(path) not in paths:
            self._data["repos"].append(str(path))
            self._save()
            return True
        return False

    def remove_repo(self, path: Path) -> bool:
        path = path.resolve()
        before = len(self._data["repos"])
        self._data["repos"] = [p for p in self._data["repos"] if Path(p).resolve() != path]
        if len(self._data["repos"]) < before:
            self._save()
            return True
        return False

    def reorder_repos(self, paths: list[Path]):
        self._data["repos"] = [str(p.resolve()) for p in paths]
        self._save()

    # ── Misc settings ─────────────────────────────────────────────────────────

    @property
    def max_log_entries(self) -> int:
        return self._data.get("max_log_entries", 80)

    @property
    def auto_fetch_interval(self) -> int:
        return self._data.get("auto_fetch_interval", 0)

    @property
    def source_dir(self) -> Path | None:
        if _SOURCE_DIR_FILE.exists():
            p = Path(_SOURCE_DIR_FILE.read_text().strip())
            return p if p.exists() else None
        return None

    @property
    def last_update_check(self) -> float:
        return float(self._data.get("last_update_check", 0.0))

    def set_last_update_check(self, ts: float) -> None:
        self._data["last_update_check"] = ts
        self._save()

    @property
    def pending_updates(self) -> int:
        return int(self._data.get("pending_updates", 0))

    def set_pending_updates(self, count: int) -> None:
        self._data["pending_updates"] = count
        self._save()
