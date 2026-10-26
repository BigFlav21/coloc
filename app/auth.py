import hashlib
import hmac
import os
import re
import time
from collections.abc import Callable

from fastapi import Depends, Request
from sqlmodel import Session

from .db import get_session
from .models import User

PIN_RE = re.compile(r"^\d{4,6}$")


def hash_pin(pin: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$")
        digest = hashlib.scrypt(pin.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


class LoginLimiter:
    """Bloque une clé (prénom) après `max_attempts` échecs, pendant `window` secondes.

    La clé est le prénom et non l'IP : derrière un reverse proxy, toutes les
    requêtes arrivent avec la même IP.
    """

    def __init__(self, max_attempts: int = 5, window: float = 900, clock: Callable[[], float] = time.monotonic):
        self.max_attempts = max_attempts
        self.window = window
        self.clock = clock
        self._fails: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        now = self.clock()
        recent = [t for t in self._fails.get(key, []) if now - t < self.window]
        self._fails[key] = recent
        return recent

    def blocked_for(self, key: str) -> int:
        recent = self._recent(key)
        if len(recent) < self.max_attempts:
            return 0
        return int(self.window - (self.clock() - recent[-1])) + 1

    def fail(self, key: str) -> None:
        self._recent(key).append(self.clock())

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)


class AuthRedirect(Exception):
    def __init__(self, url: str):
        self.url = url


def session_user(request: Request, db: Session = Depends(get_session)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if user is None:
        request.session.clear()
        raise AuthRedirect("/login")
    return user


def current_user(user: User = Depends(session_user)) -> User:
    if user.must_change_pin:
        raise AuthRedirect("/pin")
    return user
