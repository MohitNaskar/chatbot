import uuid
import time
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory session store: { session_id: { "history": [...], "last_active": float } }
#
# IMPORTANT: This is suitable for single-instance deployments.
# In a horizontally-scaled production environment, replace with Redis or a
# database-backed store. The separation here (this module only) means that
# replacement requires changes to this file alone.
_sessions: dict[str, dict] = {}


def get_or_create_session(session_id: Optional[str] = None) -> str:
    _cleanup_expired()
    if session_id and session_id in _sessions:
        _sessions[session_id]["last_active"] = time.time()
        return session_id
    new_id = str(uuid.uuid4())
    _sessions[new_id] = {"history": [], "last_active": time.time()}
    logger.debug("New session: %s", new_id)
    return new_id


def get_history(session_id: str) -> list[dict]:
    session = _sessions.get(session_id)
    return list(session["history"]) if session else []


def add_exchange(session_id: str, user_message: str, assistant_message: str) -> None:
    """Append one user+model exchange and trim to the configured limit."""
    if session_id not in _sessions:
        _sessions[session_id] = {"history": [], "last_active": time.time()}

    history = _sessions[session_id]["history"]
    history.append({"role": "user", "parts": user_message})
    history.append({"role": "model", "parts": assistant_message})

    # Keep the most recent N message pairs (N = MAX_HISTORY_MESSAGES)
    max_items = settings.MAX_HISTORY_MESSAGES * 2
    if len(history) > max_items:
        _sessions[session_id]["history"] = history[-max_items:]

    _sessions[session_id]["last_active"] = time.time()


def reset_session(session_id: str) -> None:
    if session_id in _sessions:
        _sessions[session_id]["history"] = []
        logger.info("Session reset: %s", session_id)


def _cleanup_expired() -> None:
    now = time.time()
    expired = [
        sid
        for sid, data in _sessions.items()
        if now - data["last_active"] > settings.SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.info("Expired %d sessions", len(expired))
