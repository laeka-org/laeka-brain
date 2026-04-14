"""XDG-aware user_uuid storage.

First time the server runs, it generates a UUID v4 and writes it to
~/.config/laeka-brain/user_uuid (XDG_CONFIG_HOME honoured).
All subsequent runs read from that file — no interactive prompt needed.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path


def _config_dir() -> Path:
    """Return the config dir, honouring XDG_CONFIG_HOME if set."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    return base / "laeka-brain"


def _uuid_path() -> Path:
    return _config_dir() / "user_uuid"


def get_user_uuid() -> str:
    """Return the persisted user_uuid, creating one on first call."""
    path = _uuid_path()
    if path.exists():
        stored = path.read_text().strip()
        if stored:
            return stored
    # Generate and persist a new UUID.
    new_uuid = str(uuid.uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_uuid + "\n")
    return new_uuid


def set_user_uuid(new_uuid: str) -> None:
    """Override the persisted user_uuid (used in tests / manual migration)."""
    path = _uuid_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_uuid.strip() + "\n")


def delete_user_uuid() -> None:
    """Remove the persisted user_uuid (offboarding cleanup)."""
    path = _uuid_path()
    if path.exists():
        path.unlink()
