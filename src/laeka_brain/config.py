"""XDG-aware user_uuid and API key storage.

First time the server runs, it generates a UUID v4 and writes it to
~/.config/laeka-brain/user_uuid (XDG_CONFIG_HOME honoured).
After provisioning, the JWT API key returned by /v1/brain/mini/provision is
stored in ~/.config/laeka-brain/api_key and sent as Authorization: Bearer on
all subsequent auxiliary brain calls.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

log = logging.getLogger(__name__)


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


def _api_key_path() -> Path:
    return _config_dir() / "api_key"


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


# ---------------------------------------------------------------------------
# Phase 4 — JWT API key persistence
# ---------------------------------------------------------------------------


def get_api_key() -> str | None:
    """Return the stored JWT API key, or None if not yet provisioned."""
    path = _api_key_path()
    if path.exists():
        stored = path.read_text().strip()
        if stored:
            return stored
    return None


def set_api_key(api_key: str) -> None:
    """Persist the JWT API key returned by /v1/brain/mini/provision."""
    path = _api_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(api_key.strip() + "\n")
    log.debug("brain_auth: API key persisted to %s", path)


def delete_api_key() -> None:
    """Remove the persisted API key (offboarding cleanup)."""
    path = _api_key_path()
    if path.exists():
        path.unlink()
        log.debug("brain_auth: API key removed from %s", path)
