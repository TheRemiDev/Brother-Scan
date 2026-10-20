"""Réglages modifiables depuis l'interface : code PIN (haché) et contacts favoris."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_pin(pin: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_pin(pin: str, stored: str) -> bool:
    try:
        algo, salt_hex, digest_hex = stored.split("$")
    except (ValueError, AttributeError):
        return False
    if algo != "scrypt":
        return False
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def valid_email(address: str) -> bool:
    return bool(EMAIL_RE.match(address or "")) and len(address) <= 254


class Settings:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data = {"pin_hash": "", "contacts": []}
        if path.exists():
            try:
                self._data.update(json.loads(path.read_text("utf-8")))
            except (OSError, ValueError):
                pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), "utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    # --- PIN -------------------------------------------------------------
    @property
    def pin_hash(self) -> str:
        return self._data.get("pin_hash", "")

    @property
    def has_pin(self) -> bool:
        return bool(self.pin_hash)

    def verify_pin(self, pin: str) -> bool:
        return self.has_pin and check_pin(pin, self.pin_hash)

    def set_pin(self, pin: str) -> None:
        if not pin:
            raise ValueError("Le code PIN ne peut pas être vide.")
        with self._lock:
            self._data["pin_hash"] = hash_pin(pin)
            self._save()

    # --- Données libres (Google Drive...) -----------------------------------
    def get(self, key: str, default=None):
        value = self._data.get(key, default)
        return json.loads(json.dumps(value))  # copie : rien n'est modifié par inadvertance

    def put(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    # --- Contacts --------------------------------------------------------
    @property
    def contacts(self) -> list[dict]:
        return list(self._data.get("contacts", []))

    def add_contact(self, name: str, email: str) -> dict:
        email = email.strip()
        name = (name or "").strip()[:80] or email.split("@")[0]
        if not valid_email(email):
            raise ValueError("Adresse e-mail invalide.")
        with self._lock:
            contacts = [c for c in self._data.get("contacts", []) if c["email"].lower() != email.lower()]
            contact = {"id": secrets.token_hex(6), "name": name, "email": email}
            contacts.append(contact)
            contacts.sort(key=lambda c: c["name"].lower())
            self._data["contacts"] = contacts
            self._save()
        return contact

    def remove_contact(self, contact_id: str) -> None:
        with self._lock:
            self._data["contacts"] = [c for c in self._data.get("contacts", []) if c["id"] != contact_id]
            self._save()
