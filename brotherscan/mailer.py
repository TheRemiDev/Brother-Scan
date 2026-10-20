"""Réception (IMAP) des numérisations envoyées par l'imprimante et réexpédition (SMTP)."""

from __future__ import annotations

import email
import email.policy
import email.utils
import imaplib
import json
import logging
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from pathlib import Path

from .config import Config
from .store import Store

log = logging.getLogger("brotherscan.mail")

_DATE_RE = re.compile(rb'INTERNALDATE "([^"]+)"')


def _connect_imap(cfg: Config) -> imaplib.IMAP4:
    ctx = ssl.create_default_context()
    if cfg.imap_security == "ssl":
        conn = imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port, ssl_context=ctx, timeout=30)
    else:
        conn = imaplib.IMAP4(cfg.imap_host, cfg.imap_port, timeout=30)
        if cfg.imap_security == "starttls":
            conn.starttls(ssl_context=ctx)
    conn.login(cfg.imap_user, cfg.imap_password)
    return conn


def _quote(mailbox: str) -> str:
    return '"' + mailbox.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _special_folder(conn: imaplib.IMAP4, flag: bytes) -> str | None:
    """Dossier spécial (\\Trash, \\Sent...) annoncé par le serveur."""
    typ, data = conn.list()
    if typ != "OK":
        return None
    for line in data or []:
        if not isinstance(line, bytes) or flag not in line:
            continue
        match = re.search(rb'"([^"]+)"\s*$', line) or re.search(rb"(\S+)\s*$", line)
        if match:
            return match.group(1).decode("utf-8", "replace")
    return None


def _internal_date(header: bytes, default: float) -> float:
    match = _DATE_RE.search(header)
    if match:
        parsed = imaplib.Internaldate2tuple(b'INTERNALDATE "' + match.group(1) + b'"')
        if parsed:
            return time.mktime(parsed)
    return default


def _sender_address(msg: EmailMessage) -> str:
    return email.utils.parseaddr(str(msg.get("From", "")))[1].lower()


def _pdf_parts(msg: EmailMessage) -> list[tuple[str, bytes]]:
    parts = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        name = part.get_filename() or ""
        ctype = part.get_content_type()
        if ctype == "application/pdf" or name.lower().endswith(".pdf"):
            payload = part.get_payload(decode=True)
            if payload and payload.lstrip()[:5] == b"%PDF-":
                parts.append((name or "scan.pdf", payload))
    return parts


class MailWorker:
    """Relève la boîte de réception, importe les PDF puis supprime définitivement les e-mails."""

    def __init__(self, cfg: Config, store: Store):
        self.cfg = cfg
        self.store = store
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_check: float = 0
        self.last_error: str = ""
        self._seen_file = cfg.data_dir / "imported.json"

    # --- cycle de vie -----------------------------------------------------
    def start(self) -> None:
        if not self.cfg.imap_enabled:
            log.warning("IMAP non configuré : aucune numérisation ne sera relevée.")
            return
        self._thread = threading.Thread(target=self._run, name="imap", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def poke(self) -> None:
        """Déclenche une relève immédiate (ex. ouverture de l'interface)."""
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.check_mailbox()
                self.last_error = ""
            except Exception as exc:  # réseau, identifiants...
                self.last_error = str(exc) or exc.__class__.__name__
                log.warning("Relève IMAP échouée : %s", self.last_error)
            self.last_check = time.time()
            self._wake.wait(self.cfg.poll_seconds)
            self._wake.clear()

    # --- messages déjà importés (évite les doublons si la suppression échoue) ----
    def _load_seen(self) -> dict[str, float]:
        try:
            seen = json.loads(self._seen_file.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        limit = time.time() - 2 * 86400
        return {k: v for k, v in seen.items() if v > limit}

    def _save_seen(self, seen: dict[str, float]) -> None:
        self._seen_file.write_text(json.dumps(seen), "utf-8")

    # --- relève -----------------------------------------------------------
    def check_mailbox(self) -> int:
        cfg = self.cfg
        retention = cfg.retention_hours * 3600
        now = time.time()
        imported = 0
        seen = self._load_seen()
        conn = _connect_imap(cfg)
        try:
            typ, _ = conn.select(_quote(cfg.imap_folder))
            if typ != "OK":
                raise RuntimeError(f"Dossier IMAP introuvable : {cfg.imap_folder}")
            typ, data = conn.uid("SEARCH", None, "ALL")
            uids = data[0].split() if typ == "OK" and data and data[0] else []
            to_delete: list[bytes] = []

            for uid in uids:
                typ, fetched = conn.uid("FETCH", uid, "(INTERNALDATE BODY.PEEK[])")
                if typ != "OK" or not fetched or not isinstance(fetched[0], tuple):
                    continue
                header, raw = fetched[0]
                received = min(now, _internal_date(header, now))

                msg = email.message_from_bytes(raw, policy=email.policy.default)
                key = str(msg.get("Message-ID") or "") or f"uid:{uid.decode()}:{received}"
                expires_at = received + retention

                if expires_at <= now:
                    to_delete.append(uid)  # trop ancien : suppression sans import
                    continue

                sender = _sender_address(msg)
                if cfg.allowed_senders and sender not in cfg.allowed_senders:
                    log.info("Expéditeur ignoré : %s", sender)
                    continue  # conservé dans la boîte, supprimé au bout de 24 h

                if key not in seen:
                    for index, (name, payload) in enumerate(_pdf_parts(msg)):
                        try:
                            self.store.add(payload, kind="scan", filename=name, created_at=received + index / 1000,
                                           expires_at=expires_at, sender=sender)
                            imported += 1
                        except ValueError:
                            log.warning("Pièce jointe PDF illisible ignorée (%s)", name)
                    seen[key] = now
                    self._save_seen(seen)
                to_delete.append(uid)

            if to_delete:
                self._delete(conn, to_delete)
            # Copies envoyées / corbeille du serveur : rien ne doit y rester plus de 24 h
            for flag in (b"\\Sent", b"\\All", b"\\Trash"):
                folder = _special_folder(conn, flag)
                if folder and folder != cfg.imap_folder:
                    self._purge_older(conn, folder, now - retention)
        finally:
            try:
                conn.logout()
            except Exception:
                pass
        if imported:
            log.info("%d numérisation(s) importée(s)", imported)
        return imported

    def _delete(self, conn: imaplib.IMAP4, uids: list[bytes]) -> None:
        """Suppression définitive (y compris chez Gmail, qui archive au lieu de supprimer)."""
        uid_set = b",".join(uids).decode()
        typ, caps = conn.capability()
        is_gmail = typ == "OK" and b"X-GM-EXT-1" in (caps[0] or b"")
        trash = _special_folder(conn, b"\\Trash") if is_gmail else None
        if trash:
            conn.uid("COPY", uid_set, _quote(trash))
        conn.uid("STORE", uid_set, "+FLAGS.SILENT", r"(\Deleted)")
        conn.expunge()
        if trash:
            if conn.select(_quote(trash))[0] == "OK":
                typ, data = conn.uid("SEARCH", None, "ALL")
                if typ == "OK" and data and data[0]:
                    # Uniquement les messages arrivés dans la corbeille depuis cette boîte dédiée
                    conn.uid("STORE", b",".join(data[0].split()).decode(), "+FLAGS.SILENT", r"(\Deleted)")
                    conn.expunge()
        log.info("%d e-mail(s) supprimé(s) définitivement", len(uids))

    def _purge_older(self, conn: imaplib.IMAP4, folder: str, cutoff: float) -> None:
        if conn.select(_quote(folder))[0] != "OK":
            return
        typ, data = conn.uid("SEARCH", None, "ALL")
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        old = []
        for uid in uids:
            typ, fetched = conn.uid("FETCH", uid, "(INTERNALDATE)")
            if typ == "OK" and fetched and isinstance(fetched[0], bytes):
                if _internal_date(fetched[0], time.time()) <= cutoff:
                    old.append(uid)
        if old:
            conn.uid("STORE", b",".join(old).decode(), "+FLAGS.SILENT", r"(\Deleted)")
            conn.expunge()
            log.info("%d ancien(s) e-mail(s) supprimé(s) dans %s", len(old), folder)


def send_pdf(cfg: Config, recipients: list[str], subject: str, body: str, filename: str, data: bytes) -> None:
    if not cfg.smtp_enabled:
        raise RuntimeError("L'envoi d'e-mails n'est pas configuré.")
    msg = EmailMessage()
    msg["From"] = cfg.smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    from_address = email.utils.parseaddr(cfg.smtp_from)[1] or cfg.smtp_user
    msg["Message-ID"] = email.utils.make_msgid(domain=from_address.split("@")[-1] or None)
    msg.set_content(body)
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=filename)

    ctx = ssl.create_default_context()
    if cfg.smtp_security == "ssl":
        server: smtplib.SMTP = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ctx, timeout=60)
    else:
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=60)
        if cfg.smtp_security == "starttls":
            server.starttls(context=ctx)
    try:
        if cfg.smtp_user and cfg.smtp_password:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def test_connections(cfg: Config) -> list[tuple[str, bool, str]]:
    results = []
    try:
        conn = _connect_imap(cfg)
        ok = conn.select(_quote(cfg.imap_folder))[0] == "OK"
        conn.logout()
        results.append(("IMAP", ok, "connexion réussie" if ok else f"dossier {cfg.imap_folder} introuvable"))
    except Exception as exc:
        results.append(("IMAP", False, str(exc)))
    try:
        ctx = ssl.create_default_context()
        if cfg.smtp_security == "ssl":
            server: smtplib.SMTP = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=ctx, timeout=20)
        else:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20)
            if cfg.smtp_security == "starttls":
                server.starttls(context=ctx)
        if cfg.smtp_user and cfg.smtp_password:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.quit()
        results.append(("SMTP", True, "connexion réussie"))
    except Exception as exc:
        results.append(("SMTP", False, str(exc)))
    return results
