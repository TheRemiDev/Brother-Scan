"""Google Drive : connexion OAuth des comptes, choix du dossier et envoi des PDF (API REST, sans dépendance)."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .settings import Settings

log = logging.getLogger("brotherscan.drive")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3/files"
# Accès complet nécessaire pour parcourir et choisir un dossier existant du Drive
SCOPES = "openid email https://www.googleapis.com/auth/drive"
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveError(Exception):
    """Erreur affichable telle quelle dans l'interface."""


def _request(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None,
             timeout: int = 60) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DriveError("Google Drive est injoignable pour le moment.") from exc


def _json(body: bytes) -> dict:
    try:
        return json.loads(body or b"{}")
    except ValueError:
        return {}


def _google_message(body: bytes) -> str:
    data = _json(body)
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message", ""))[:200]
    return str(data.get("error_description") or err or "")[:200]


def _escape_q(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class Drive:
    def __init__(self, settings: Settings, public_url: str):
        self.settings = settings
        self.redirect_uri = public_url.rstrip("/") + "/api/drive/callback"
        self._lock = threading.Lock()
        self._states: dict[str, float] = {}
        self._tokens: dict[str, tuple[str, float]] = {}  # compte -> (jeton d'accès, expiration)

    # --- données ------------------------------------------------------------
    def _data(self) -> dict:
        data = self.settings.get("drive", {}) or {}
        data.setdefault("accounts", [])
        data.setdefault("destinations", [])
        return data

    def _save(self, data: dict) -> None:
        self.settings.put("drive", data)

    @property
    def configured(self) -> bool:
        data = self._data()
        return bool(data.get("client_id") and data.get("client_secret"))

    def public_state(self) -> dict:
        data = self._data()
        accounts = {a["id"]: a for a in data["accounts"]}
        return {
            "configured": self.configured,
            "client_id": data.get("client_id", ""),
            "redirect_uri": self.redirect_uri,
            "accounts": [{"id": a["id"], "email": a["email"]} for a in data["accounts"]],
            "destinations": [
                {
                    "id": d["id"], "account_id": d["account_id"], "label": d["label"],
                    "folder_id": d["folder_id"], "folder_path": d["folder_path"],
                    "email": accounts.get(d["account_id"], {}).get("email", ""),
                }
                for d in data["destinations"] if d["account_id"] in accounts
            ],
        }

    def set_client(self, client_id: str, client_secret: str) -> None:
        client_id, client_secret = client_id.strip(), client_secret.strip()
        if not client_id.endswith(".apps.googleusercontent.com"):
            raise DriveError("L’ID client doit se terminer par « .apps.googleusercontent.com ».")
        if not client_secret:
            raise DriveError("Le code secret du client est requis.")
        with self._lock:
            data = self._data()
            data["client_id"], data["client_secret"] = client_id, client_secret
            self._save(data)

    # --- connexion OAuth ------------------------------------------------------
    def auth_url(self) -> str:
        if not self.configured:
            raise DriveError("Renseignez d’abord les identifiants Google.")
        state = secrets.token_urlsafe(24)
        now = time.time()
        with self._lock:
            self._states = {k: v for k, v in self._states.items() if v > now}
            self._states[state] = now + 600
        params = {
            "client_id": self._data()["client_id"], "redirect_uri": self.redirect_uri,
            "response_type": "code", "scope": SCOPES, "access_type": "offline",
            "prompt": "consent select_account", "include_granted_scopes": "true", "state": state,
        }
        return AUTH_URL + "?" + urllib.parse.urlencode(params)

    def complete(self, state: str, code: str) -> str:
        """Termine la connexion ; renvoie l'identifiant du compte."""
        with self._lock:
            expires = self._states.pop(state, 0)
        if expires < time.time():
            raise DriveError("Lien de connexion expiré : recommencez depuis les réglages.")
        data = self._data()
        status, _, body = _request("POST", TOKEN_URL, data=urllib.parse.urlencode({
            "code": code, "client_id": data["client_id"], "client_secret": data["client_secret"],
            "redirect_uri": self.redirect_uri, "grant_type": "authorization_code",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        tokens = _json(body)
        if status != 200 or "access_token" not in tokens:
            raise DriveError(f"Google a refusé la connexion ({_google_message(body) or status}).")
        if "https://www.googleapis.com/auth/drive" not in tokens.get("scope", ""):
            raise DriveError("L’accès au Drive n’a pas été autorisé : cochez la case Google Drive lors de la connexion.")
        status, _, body = _request("GET", USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        email = _json(body).get("email", "") if status == 200 else ""

        with self._lock:
            data = self._data()
            account = next((a for a in data["accounts"] if email and a["email"].lower() == email.lower()), None)
            if account is None:
                account = {"id": secrets.token_hex(6), "email": email or "Compte Google"}
                data["accounts"].append(account)
            if tokens.get("refresh_token"):
                account["refresh_token"] = tokens["refresh_token"]
            if not account.get("refresh_token"):
                raise DriveError("Google n’a pas fourni d’accès permanent : retirez l’application de votre compte Google puis recommencez.")
            self._save(data)
            self._tokens[account["id"]] = (tokens["access_token"], time.time() + int(tokens.get("expires_in", 3600)) - 60)
        log.info("Compte Google connecté : %s", account["email"])
        return account["id"]

    def _access_token(self, account_id: str) -> str:
        cached = self._tokens.get(account_id)
        if cached and cached[1] > time.time():
            return cached[0]
        data = self._data()
        account = next((a for a in data["accounts"] if a["id"] == account_id), None)
        if not account:
            raise DriveError("Ce compte Google n’existe plus.")
        status, _, body = _request("POST", TOKEN_URL, data=urllib.parse.urlencode({
            "client_id": data.get("client_id", ""), "client_secret": data.get("client_secret", ""),
            "refresh_token": account.get("refresh_token", ""), "grant_type": "refresh_token",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        tokens = _json(body)
        if status != 200 or "access_token" not in tokens:
            if tokens.get("error") == "invalid_grant":
                raise DriveError(f"L’accès au Drive de {account['email']} a expiré : reconnectez ce compte dans les réglages.")
            raise DriveError(f"Google a refusé l’accès ({_google_message(body) or status}).")
        self._tokens[account_id] = (tokens["access_token"], time.time() + int(tokens.get("expires_in", 3600)) - 60)
        return tokens["access_token"]

    def _api(self, account_id: str, method: str, url: str, **kwargs) -> tuple[int, dict, bytes]:
        headers = {"Authorization": f"Bearer {self._access_token(account_id)}", **kwargs.pop("headers", {})}
        status, res_headers, body = _request(method, url, headers=headers, **kwargs)
        if status == 401:  # jeton révoqué entre-temps : un nouvel essai
            self._tokens.pop(account_id, None)
            headers["Authorization"] = f"Bearer {self._access_token(account_id)}"
            status, res_headers, body = _request(method, url, headers=headers, **kwargs)
        if status >= 400:
            raise DriveError(f"Google Drive a refusé l’opération ({_google_message(body) or status}).")
        return status, res_headers, body

    # --- dossiers ---------------------------------------------------------------
    def list_folders(self, account_id: str, parent: str = "root") -> list[dict]:
        if not parent.replace("-", "").replace("_", "").isalnum():
            raise DriveError("Dossier invalide.")
        query = f"'{_escape_q(parent)}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false"
        folders, page = [], ""
        while True:
            params = {"q": query, "fields": "nextPageToken, files(id, name)", "orderBy": "name_natural",
                      "pageSize": "200", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            if page:
                params["pageToken"] = page
            _, _, body = self._api(account_id, "GET", f"{API}/files?{urllib.parse.urlencode(params)}")
            data = _json(body)
            folders += [{"id": f["id"], "name": f["name"]} for f in data.get("files", [])]
            page = data.get("nextPageToken", "")
            if not page or len(folders) >= 1000:
                return folders

    def create_folder(self, account_id: str, parent: str, name: str) -> dict:
        name = name.strip()[:200]
        if not name:
            raise DriveError("Donnez un nom au dossier.")
        meta = json.dumps({"name": name, "mimeType": FOLDER_MIME, "parents": [parent or "root"]}).encode()
        _, _, body = self._api(account_id, "POST", f"{API}/files?supportsAllDrives=true&fields=id,name",
                               data=meta, headers={"Content-Type": "application/json; charset=utf-8"})
        folder = _json(body)
        return {"id": folder["id"], "name": folder["name"]}

    # --- destinations (compte + dossier) -------------------------------------------
    def save_destination(self, *, destination_id: str | None, account_id: str, label: str,
                         folder_id: str, folder_path: str) -> dict:
        with self._lock:
            data = self._data()
            if not any(a["id"] == account_id for a in data["accounts"]):
                raise DriveError("Compte Google inconnu.")
            label = (label or "").strip()[:80] or folder_path.split(" / ")[-1] or "Google Drive"
            dest = next((d for d in data["destinations"] if d["id"] == destination_id), None) if destination_id else None
            if dest is None:
                dest = {"id": secrets.token_hex(6)}
                data["destinations"].append(dest)
            dest.update(account_id=account_id, label=label, folder_id=folder_id or "root",
                        folder_path=(folder_path or "Mon Drive")[:500])
            self._save(data)
            return dict(dest)

    def remove_destination(self, destination_id: str) -> None:
        with self._lock:
            data = self._data()
            dest = next((d for d in data["destinations"] if d["id"] == destination_id), None)
            if not dest:
                return
            data["destinations"].remove(dest)
            orphan = None
            if not any(d["account_id"] == dest["account_id"] for d in data["destinations"]):
                orphan = next((a for a in data["accounts"] if a["id"] == dest["account_id"]), None)
                if orphan:
                    data["accounts"].remove(orphan)
                    self._tokens.pop(orphan["id"], None)
            self._save(data)
        if orphan and orphan.get("refresh_token"):
            # Plus aucun dossier n'utilise ce compte : l'accès est retiré chez Google
            _request("POST", REVOKE_URL, data=urllib.parse.urlencode({"token": orphan["refresh_token"]}).encode(),
                     headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)

    def destination(self, destination_id: str) -> dict:
        dest = next((d for d in self._data()["destinations"] if d["id"] == destination_id), None)
        if not dest:
            raise DriveError("Ce dossier Drive n’est plus configuré.")
        return dest

    # --- envoi ----------------------------------------------------------------------
    def upload(self, destination_id: str, filename: str, data: bytes) -> dict:
        dest = self.destination(destination_id)
        meta = json.dumps({"name": filename, "mimeType": "application/pdf", "parents": [dest["folder_id"]]}).encode()
        # Envoi « resumable » : fiable même pour les gros scans
        _, headers, _ = self._api(
            dest["account_id"], "POST", f"{UPLOAD_API}?uploadType=resumable&supportsAllDrives=true&fields=id,name,webViewLink",
            data=meta, headers={"Content-Type": "application/json; charset=utf-8",
                                "X-Upload-Content-Type": "application/pdf",
                                "X-Upload-Content-Length": str(len(data))},
        )
        location = next((v for k, v in headers.items() if k.lower() == "location"), "")
        if not location.startswith("https://"):
            raise DriveError("Google Drive n’a pas accepté l’envoi.")
        _, _, body = self._api(dest["account_id"], "PUT", location, data=data,
                               headers={"Content-Type": "application/pdf"}, timeout=300)
        file = _json(body)
        log.info("Envoyé dans Google Drive (%s) : %s", dest["label"], file.get("id"))
        return {"id": file.get("id", ""), "link": file.get("webViewLink") or
                f"https://drive.google.com/file/d/{file.get('id', '')}/view"}
