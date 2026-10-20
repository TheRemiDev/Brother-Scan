"""Faux serveurs Google (OAuth + Drive) pour les tests, branchés sur brotherscan.drive._request."""

import json
import urllib.parse

from brotherscan import drive


class FakeGoogle:
    def __init__(self):
        self.folders = {"root": [("f1", "Factures"), ("f2", "Impôts")], "f1": [("f11", "2026")]}
        self.uploads = []  # (nom, parents, taille)
        self.revoked = []
        self.refresh_ok = True
        self._pending = None

    def __call__(self, method, url, *, data=None, headers=None, timeout=60):
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        form = urllib.parse.parse_qs((data or b"").decode()) if headers and "x-www-form-urlencoded" in headers.get("Content-Type", "") else {}
        ok = lambda body, h=None: (200, h or {}, json.dumps(body).encode())  # noqa: E731
        if url.startswith(drive.TOKEN_URL):
            if form.get("grant_type") == ["authorization_code"]:
                return ok({"access_token": "at1", "refresh_token": "rt1", "expires_in": 3600,
                           "scope": "openid https://www.googleapis.com/auth/drive email"})
            if not self.refresh_ok:
                return 400, {}, json.dumps({"error": "invalid_grant"}).encode()
            return ok({"access_token": "at2", "expires_in": 3600})
        if url.startswith(drive.USERINFO_URL):
            return ok({"email": "remi@gmail.com"})
        if url.startswith(drive.REVOKE_URL):
            self.revoked.append(form.get("token"))
            return ok({})
        if url.startswith(drive.API + "/files") and method == "GET":
            parent = qs["q"][0].split("'")[1]
            return ok({"files": [{"id": i, "name": n} for i, n in self.folders.get(parent, [])]})
        if url.startswith(drive.API + "/files") and method == "POST":
            meta = json.loads(data)
            new_id = "n%d" % len(self.folders)
            self.folders.setdefault(meta["parents"][0], []).append((new_id, meta["name"]))
            return ok({"id": new_id, "name": meta["name"]})
        if url.startswith(drive.UPLOAD_API) and method == "POST":
            self._pending = json.loads(data)
            assert "fields=id" in url
            return 200, {"Location": "https://www.googleapis.com/upload/drive/v3/files?upload_id=xyz"}, b""
        if "upload_id=xyz" in url and method == "PUT":
            self.uploads.append((self._pending["name"], self._pending["parents"], len(data)))
            return ok({"id": "file1", "name": self._pending["name"], "webViewLink": "https://drive.google.com/file/d/file1/view"})
        raise AssertionError(f"requête inattendue {method} {url}")


def install():
    fake = FakeGoogle()
    drive._request = fake
    return fake
