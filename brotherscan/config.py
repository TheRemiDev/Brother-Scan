"""Configuration, lue depuis les variables d'environnement (fichier /etc/brother-scan/brother-scan.env)."""

from __future__ import annotations

import os
import secrets
import shlex
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name, "1" if default else "0").lower()
    return value in {"1", "true", "yes", "oui", "on"}


@dataclass(frozen=True)
class Config:
    data_dir: Path
    public_url: str
    scan_address: str
    secret_key: str
    retention_hours: int
    poll_seconds: int
    session_hours: int
    cookie_secure: bool

    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folder: str
    imap_security: str  # ssl | starttls | none

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_security: str  # ssl | starttls | none

    allowed_senders: tuple[str, ...] = field(default_factory=tuple)
    max_visible: int = 10

    @property
    def imap_enabled(self) -> bool:
        return bool(self.imap_host and self.imap_user)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host)

    @property
    def scans_dir(self) -> Path:
        return self.data_dir / "scans"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


def load_env_file(path: str) -> None:
    """Charge un fichier KEY='valeur' (format écrit par install.sh) sans écraser l'environnement."""
    try:
        lines = Path(path).read_text("utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        try:
            parts = shlex.split(raw)
        except ValueError:
            continue
        os.environ.setdefault(key.strip(), parts[0] if parts else "")


def load_config() -> Config:
    if _env("BS_ENV_FILE"):
        load_env_file(_env("BS_ENV_FILE"))
    data_dir = Path(_env("BS_DATA_DIR", "./data")).resolve()
    secret = _env("BS_SECRET_KEY")
    if not secret:
        # Clé persistée dans le dossier de données si non fournie (mode développement).
        data_dir.mkdir(parents=True, exist_ok=True)
        key_file = data_dir / ".secret_key"
        if key_file.exists():
            secret = key_file.read_text().strip()
        else:
            secret = secrets.token_hex(32)
            key_file.write_text(secret)
            key_file.chmod(0o600)

    imap_user = _env("BS_IMAP_USER")
    smtp_user = _env("BS_SMTP_USER", imap_user)
    senders = tuple(s.strip().lower() for s in _env("BS_ALLOWED_SENDERS").split(",") if s.strip())

    return Config(
        data_dir=data_dir,
        public_url=_env("BS_PUBLIC_URL", "http://localhost:8710"),
        scan_address=_env("BS_SCAN_ADDRESS", imap_user or "scan@remividon.fr"),
        secret_key=secret,
        retention_hours=max(1, _env_int("BS_RETENTION_HOURS", 24)),
        poll_seconds=max(5, _env_int("BS_POLL_SECONDS", 20)),
        session_hours=max(1, _env_int("BS_SESSION_HOURS", 12)),
        cookie_secure=_env_bool("BS_COOKIE_SECURE", _env("BS_PUBLIC_URL").startswith("https://")),
        imap_host=_env("BS_IMAP_HOST"),
        imap_port=_env_int("BS_IMAP_PORT", 993),
        imap_user=imap_user,
        imap_password=_env("BS_IMAP_PASSWORD"),
        imap_folder=_env("BS_IMAP_FOLDER", "INBOX"),
        imap_security=_env("BS_IMAP_SECURITY", "ssl").lower(),
        smtp_host=_env("BS_SMTP_HOST"),
        smtp_port=_env_int("BS_SMTP_PORT", 465),
        smtp_user=smtp_user,
        smtp_password=_env("BS_SMTP_PASSWORD", _env("BS_IMAP_PASSWORD")),
        smtp_from=_env("BS_SMTP_FROM", smtp_user),
        smtp_security=_env("BS_SMTP_SECURITY", "ssl").lower(),
        allowed_senders=senders,
    )
