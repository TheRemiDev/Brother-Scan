"""Stockage des numérisations sur disque, avec expiration stricte."""

from __future__ import annotations

import json
import logging
import secrets
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import pdftools

log = logging.getLogger("brotherscan.store")


@dataclass
class Scan:
    id: str
    kind: str  # "scan" | "merge"
    filename: str
    created_at: float
    expires_at: float
    pages: int
    size: int
    sender: str = ""
    sources: list[str] = field(default_factory=list)

    def public(self) -> dict:
        data = asdict(self)
        data.pop("sender", None)
        return data


class Store:
    def __init__(self, scans_dir: Path, cache_dir: Path):
        self.scans_dir = scans_dir
        self.cache_dir = cache_dir
        self._lock = threading.RLock()
        scans_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.version = 0  # incrémenté à chaque changement (rafraîchissement de l'interface)

    # --- chemins ----------------------------------------------------------
    def pdf_path(self, scan_id: str) -> Path:
        return self.scans_dir / f"{scan_id}.pdf"

    def meta_path(self, scan_id: str) -> Path:
        return self.scans_dir / f"{scan_id}.json"

    def thumb_path(self, scan_id: str) -> Path:
        return self.cache_dir / scan_id / "thumb.jpg"

    def page_path(self, scan_id: str, page: int) -> Path:
        return self.cache_dir / scan_id / f"page-{page}.jpg"

    # --- lecture ----------------------------------------------------------
    def get(self, scan_id: str) -> Scan | None:
        if not scan_id.isalnum():
            return None
        path = self.meta_path(scan_id)
        try:
            scan = Scan(**json.loads(path.read_text("utf-8")))
        except (OSError, ValueError, TypeError):
            return None
        if scan.expires_at <= time.time():
            return None
        return scan

    def all(self) -> list[Scan]:
        scans = []
        for meta in self.scans_dir.glob("*.json"):
            scan = self.get(meta.stem)
            if scan:
                scans.append(scan)
        scans.sort(key=lambda s: s.created_at, reverse=True)
        return scans

    # --- écriture ---------------------------------------------------------
    def add(self, data: bytes, *, kind: str, filename: str, created_at: float, expires_at: float,
            sender: str = "", sources: list[str] | None = None) -> Scan:
        info = pdftools.inspect(data)  # lève ValueError si le PDF est illisible
        scan_id = secrets.token_hex(8)
        with self._lock:
            pdf = self.pdf_path(scan_id)
            pdf.write_bytes(data)
            pdf.chmod(0o600)
            scan = Scan(
                id=scan_id, kind=kind, filename=filename, created_at=created_at,
                expires_at=expires_at, pages=info["pages"], size=len(data),
                sender=sender, sources=sources or [],
            )
            try:
                thumb = self.thumb_path(scan_id)
                thumb.parent.mkdir(parents=True, exist_ok=True)
                thumb.write_bytes(pdftools.render_page(data, 0, width=480))
            except Exception:  # l'aperçu n'est pas indispensable
                log.exception("Miniature impossible pour %s", scan_id)
            self.meta_path(scan_id).write_text(json.dumps(asdict(scan)), "utf-8")
            self.version += 1
        log.info("Ajouté %s (%s, %d pages)", scan_id, kind, scan.pages)
        return scan

    def delete(self, scan_id: str) -> None:
        with self._lock:
            for path in (self.pdf_path(scan_id), self.meta_path(scan_id)):
                path.unlink(missing_ok=True)
            shutil.rmtree(self.cache_dir / scan_id, ignore_errors=True)
            self.version += 1
        log.info("Supprimé %s", scan_id)

    def purge_expired(self) -> int:
        """Supprime définitivement tout ce qui a dépassé sa date d'expiration."""
        now = time.time()
        removed = 0
        with self._lock:
            known = set()
            for meta in list(self.scans_dir.glob("*.json")):
                try:
                    expires_at = json.loads(meta.read_text("utf-8"))["expires_at"]
                except (OSError, ValueError, KeyError, TypeError):
                    expires_at = 0
                if expires_at <= now:
                    self.delete(meta.stem)
                    removed += 1
                else:
                    known.add(meta.stem)
            # Fichiers orphelins (PDF sans métadonnées, cache sans scan, temporaires)
            for path in self.scans_dir.iterdir():
                if path.stem not in known:
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        path.unlink(missing_ok=True)
            for path in self.cache_dir.iterdir():
                if path.name not in known:
                    shutil.rmtree(path, ignore_errors=True)
        return removed

    def page_image(self, scan: Scan, page: int) -> bytes:
        cached = self.page_path(scan.id, page)
        if cached.exists():
            return cached.read_bytes()
        image = pdftools.render_page(self.pdf_path(scan.id).read_bytes(), page, width=1400)
        with self._lock:
            if self.meta_path(scan.id).exists():
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(image)
        return image
