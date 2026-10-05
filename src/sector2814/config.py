"""Paths and configuration for the crown.

Everything lives under the user's home by default:

    ~/.local/share/sector2814/   data (battery.db, audit.jsonl)
    ~/.config/sector2814/        policy (book-of-oa.toml) and user jewels
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    home: Path
    data_dir: Path
    config_dir: Path
    plugin_dirs: tuple[Path, ...]
    battery_path: Path
    audit_path: Path
    book_path: Path


def load_config(repo_root: Path | None = None, home: Path | None = None) -> Config:
    if home is None:
        home = Path(os.environ.get("SECTOR2814_HOME", "") or Path.home())
    if repo_root is None:
        repo_root = Path.cwd()

    data_dir = home / ".local" / "share" / "sector2814"
    config_dir = home / ".config" / "sector2814"

    return Config(
        home=home,
        data_dir=data_dir,
        config_dir=config_dir,
        plugin_dirs=(repo_root / "plugins", config_dir / "plugins"),
        battery_path=data_dir / "battery.db",
        audit_path=data_dir / "audit.jsonl",
        book_path=config_dir / "book-of-oa.toml",
    )
