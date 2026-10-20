"""Application web Brother Scan."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import __version__, auth, pdftools
from .config import load_config
from .mailer import MailWorker, send_pdf
from .settings import Settings, valid_email
from .store import Scan, Store

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/Paris")
except Exception:  # tzdata absent
    TZ = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("brotherscan")

STATIC = Path(__file__).parent / "static"

cfg = load_config()
store = Store(cfg.scans_dir, cfg.cache_dir)
settings = Settings(cfg.data_dir / "settings.json")
mail = MailWorker(cfg, store)
throttle = auth.Throttle()
_stop = threading.Event()


def _janitor() -> None:
    while not _stop.is_set():
        try:
            store.purge_expired()
        except Exception:
            log.exception("Nettoyage impossible")
        _stop.wait(60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.purge_expired()
    threading.Thread(target=_janitor, name="janitor", daemon=True).start()
    mail.start()
    yield
    _stop.set()
    mail.stop()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "frame-src 'self' blob:; object-src 'self' blob:; base-uri 'none'; form-action 'self'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# --- utilitaires -------------------------------------------------------------
def _local(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, TZ) if TZ else datetime.fromtimestamp(ts)


def _download_name(scan: Scan) -> str:
    stamp = _local(scan.created_at).strftime("%Y-%m-%d_%Hh%M")
    prefix = "Fusion" if scan.kind == "merge" else "Scan"
    return f"{prefix}_{stamp}.pdf"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def require_session(request: Request) -> None:
    if not check_session(request):
        raise HTTPException(401, "Session expirée")


def check_session(request: Request) -> bool:
    return auth.check_token(request.cookies.get(auth.COOKIE_NAME), cfg.secret_key, settings.pin_hash)


def get_scan(scan_id: str) -> Scan:
    scan = store.get(scan_id)
    if not scan:
        raise HTTPException(404, "Ce document n'existe plus (supprimé après 24 h).")
    return scan


def _set_session_cookie(response: Response) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(cfg.secret_key, settings.pin_hash, cfg.session_hours),
        max_age=cfg.session_hours * 3600,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="strict",
        path="/",
    )


def _scan_json(scan: Scan) -> dict:
    data = scan.public()
    data["download_name"] = _download_name(scan)
    return data


# --- session -----------------------------------------------------------------
class LoginBody(BaseModel):
    pin: str = Field(max_length=4096)


@app.get("/api/session")
def session(request: Request):
    return {
        "authenticated": check_session(request),
        "configured": settings.has_pin,
        "scan_address": cfg.scan_address,
        "retention_hours": cfg.retention_hours,
        "version": __version__,
    }


@app.post("/api/login")
async def login(body: LoginBody, request: Request):
    ip = _client_ip(request)
    wait = throttle.retry_after(ip)
    if wait:
        return JSONResponse({"detail": "Trop d'essais. Patientez un instant.", "retry_after": wait}, 429)
    ok = await run_in_threadpool(settings.verify_pin, body.pin)
    if not ok:
        delay = throttle.failure(ip)
        log.warning("Code PIN incorrect depuis %s", ip)
        return JSONResponse({"detail": "Code incorrect.", "retry_after": delay}, 401)
    throttle.success(ip)
    mail.poke()
    response = JSONResponse({"ok": True})
    _set_session_cookie(response)
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return response


class PinBody(BaseModel):
    current: str = Field(max_length=4096)
    new: str = Field(min_length=1, max_length=4096)


@app.post("/api/pin", dependencies=[Depends(require_session)])
async def change_pin(body: PinBody, request: Request):
    ip = _client_ip(request)
    if throttle.retry_after(ip):
        raise HTTPException(429, "Trop d'essais. Patientez un instant.")
    if not await run_in_threadpool(settings.verify_pin, body.current):
        throttle.failure(ip)
        raise HTTPException(400, "Le code actuel est incorrect.")
    await run_in_threadpool(settings.set_pin, body.new)
    log.info("Code PIN modifié")
    response = JSONResponse({"ok": True})
    _set_session_cookie(response)  # nouvelle signature pour la session en cours
    return response


# --- numérisations -------------------------------------------------------------
_last_poke = 0.0


@app.get("/api/scans", dependencies=[Depends(require_session)])
def list_scans():
    global _last_poke
    if time.time() - _last_poke > 8:
        _last_poke = time.time()
        mail.poke()
    scans = store.all()[: cfg.max_visible]
    return {
        "scans": [_scan_json(s) for s in scans],
        "now": time.time(),
        "mail": {
            "enabled": cfg.imap_enabled,
            "last_check": mail.last_check,
            "error": bool(mail.last_error),
        },
        "can_send": cfg.smtp_enabled,
    }


@app.get("/api/scans/{scan_id}/thumb", dependencies=[Depends(require_session)])
def thumb(scan_id: str):
    scan = get_scan(scan_id)
    path = store.thumb_path(scan.id)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdftools.render_page(store.pdf_path(scan.id).read_bytes(), 0, width=480))
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/scans/{scan_id}/pages/{page}", dependencies=[Depends(require_session)])
def page(scan_id: str, page: int):
    scan = get_scan(scan_id)
    if not 0 <= page < scan.pages:
        raise HTTPException(404, "Page introuvable")
    return Response(store.page_image(scan, page), media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/scans/{scan_id}/file", dependencies=[Depends(require_session)])
def download(scan_id: str, inline: bool = False):
    scan = get_scan(scan_id)
    return FileResponse(
        store.pdf_path(scan.id), media_type="application/pdf", filename=_download_name(scan),
        content_disposition_type="inline" if inline else "attachment",
        headers={"Cache-Control": "private, no-store"},
    )


@app.delete("/api/scans/{scan_id}", dependencies=[Depends(require_session)])
def delete(scan_id: str):
    store.delete(get_scan(scan_id).id)
    return {"ok": True}


class MergeBody(BaseModel):
    ids: list[str] = Field(min_length=2, max_length=50)


@app.post("/api/merge", dependencies=[Depends(require_session)])
async def merge(body: MergeBody):
    scans = [get_scan(i) for i in body.ids]
    documents = [store.pdf_path(s.id).read_bytes() for s in scans]
    data = await run_in_threadpool(pdftools.merge, documents)
    merged = await run_in_threadpool(
        lambda: store.add(
            data, kind="merge", filename="fusion.pdf", created_at=time.time(),
            # Le document fusionné disparaît en même temps que le plus ancien de ses scans
            expires_at=min(s.expires_at for s in scans), sources=[s.id for s in scans],
        )
    )
    return _scan_json(merged)


class SendBody(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=20)
    message: str = Field(default="", max_length=5000)


@app.post("/api/scans/{scan_id}/send", dependencies=[Depends(require_session)])
async def send(scan_id: str, body: SendBody):
    scan = get_scan(scan_id)
    recipients = list(dict.fromkeys(r.strip() for r in body.recipients if r.strip()))
    invalid = [r for r in recipients if not valid_email(r)]
    if invalid or not recipients:
        raise HTTPException(400, f"Adresse invalide : {', '.join(invalid) or '—'}")
    when = _local(scan.created_at)
    subject = f"Document numérisé du {when:%d/%m/%Y} à {when:%Hh%M}"
    text = body.message.strip()
    text = (text + "\n\n" if text else "") + "Vous trouverez le document en pièce jointe.\n"
    try:
        await run_in_threadpool(send_pdf, cfg, recipients, subject, text, _download_name(scan),
                                store.pdf_path(scan.id).read_bytes())
    except Exception as exc:
        log.exception("Envoi impossible")
        raise HTTPException(502, "L'envoi a échoué. Vérifiez la configuration e-mail.") from exc
    log.info("Document %s envoyé à %d destinataire(s)", scan.id, len(recipients))
    return {"ok": True}


# --- contacts --------------------------------------------------------------------
class ContactBody(BaseModel):
    name: str = Field(default="", max_length=200)
    email: str = Field(max_length=254)


@app.get("/api/contacts", dependencies=[Depends(require_session)])
def contacts():
    return {"contacts": settings.contacts}


@app.post("/api/contacts", dependencies=[Depends(require_session)])
def add_contact(body: ContactBody):
    try:
        return settings.add_contact(body.name, body.email)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/contacts/{contact_id}", dependencies=[Depends(require_session)])
def remove_contact(contact_id: str):
    settings.remove_contact(contact_id)
    return {"ok": True}


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__}


_INDEX = (STATIC / "index.html").read_text("utf-8").replace("{{VERSION}}", __version__)


@app.get("/")
def index():
    return Response(_INDEX, media_type="text/html", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC), name="static")
