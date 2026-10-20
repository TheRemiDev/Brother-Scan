"""Sessions signées et protection contre les tentatives de PIN répétées."""

from __future__ import annotations

import hashlib
import hmac
import threading
import time

COOKIE_NAME = "bs_session"


def _signature(secret: str, expires: int, pin_hash: str) -> str:
    # Le hash du PIN entre dans la signature : changer le PIN déconnecte toutes les sessions.
    msg = f"{expires}|{pin_hash}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def make_token(secret: str, pin_hash: str, hours: int) -> str:
    expires = int(time.time() + hours * 3600)
    return f"{expires}.{_signature(secret, expires, pin_hash)}"


def check_token(token: str | None, secret: str, pin_hash: str) -> bool:
    if not token or not pin_hash or "." not in token:
        return False
    raw_exp, sig = token.split(".", 1)
    try:
        expires = int(raw_exp)
    except ValueError:
        return False
    if expires < time.time():
        return False
    return hmac.compare_digest(sig, _signature(secret, expires, pin_hash))


class Throttle:
    """Après 5 erreurs, blocage progressif : 30 s, 1 min, 2 min... jusqu'à 1 h."""

    FREE_ATTEMPTS = 5

    def __init__(self):
        self._lock = threading.Lock()
        self._state: dict[str, tuple[int, float]] = {}

    def retry_after(self, key: str) -> int:
        with self._lock:
            failures, until = self._state.get(key, (0, 0))
        return max(0, int(until - time.time() + 0.999))

    def failure(self, key: str) -> int:
        with self._lock:
            failures, _ = self._state.get(key, (0, 0))
            failures += 1
            delay = 0
            if failures >= self.FREE_ATTEMPTS:
                delay = min(3600, 30 * 2 ** (failures - self.FREE_ATTEMPTS))
            self._state[key] = (failures, time.time() + delay)
            if len(self._state) > 10_000:
                self._state.clear()
            return delay

    def success(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)
