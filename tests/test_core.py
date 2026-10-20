"""Tests de base : python -m pytest tests (ou python tests/test_core.py)."""

import email.utils
import imaplib
import io
import os
import sys
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from brotherscan import auth, mailer, pdftools  # noqa: E402
from brotherscan.config import load_config  # noqa: E402
from brotherscan.settings import Settings, check_pin, hash_pin  # noqa: E402
from brotherscan.store import Store  # noqa: E402


def make_pdf(pages=1):
    images = [Image.new("RGB", (620, 877), "white") for _ in range(pages)]
    buf = io.BytesIO()
    images[0].save(buf, "PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


def make_mail(sender="printer@remividon.fr", pages=1, msgid=None):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "scan@remividon.fr"
    msg["Subject"] = "Scan"
    msg["Message-ID"] = msgid or email.utils.make_msgid()
    msg.set_content("scan")
    msg.add_attachment(make_pdf(pages), maintype="application", subtype="pdf", filename="20261020.pdf")
    return msg.as_bytes()


class FakeImap:
    """Imite le strict nécessaire d'imaplib.IMAP4."""

    def __init__(self, folders):
        self.folders = folders  # nom -> {uid: (timestamp, raw)}
        self.current = None
        self.flags = set()

    def select(self, name):
        self.current = name.strip('"')
        return ("OK", [b"1"]) if self.current in self.folders else ("NO", [b""])

    def uid(self, command, *args):
        box = self.folders[self.current]
        if command == "SEARCH":
            return "OK", [b" ".join(str(u).encode() for u in sorted(box))]
        if command == "FETCH":
            uid = int(args[0])
            ts, raw = box[uid]
            date = imaplib.Time2Internaldate(ts).encode()
            head = b"1 (UID %d INTERNALDATE %s" % (uid, date)
            if "BODY" in args[1]:
                return "OK", [(head + b" BODY[] {%d}" % len(raw), raw), b")"]
            return "OK", [head + b")"]
        if command == "STORE":
            self.flags |= {(self.current, int(u)) for u in args[0].split(",")}
            return "OK", []
        if command == "COPY":
            return "OK", []
        raise AssertionError(command)

    def expunge(self):
        box = self.folders[self.current]
        for folder, uid in list(self.flags):
            if folder == self.current:
                box.pop(uid, None)
                self.flags.discard((folder, uid))
        return "OK", []

    def capability(self):
        return "OK", [b"IMAP4rev1 MOVE"]

    def list(self):
        return "OK", [b'(\\HasNoChildren \\Sent) "/" "Sent"', b'(\\HasNoChildren) "/" "INBOX"']

    def logout(self):
        return "BYE", []


def setup(tmp, allowed=""):
    os.environ.update({"BS_DATA_DIR": tmp, "BS_IMAP_HOST": "imap.test", "BS_IMAP_USER": "scan@remividon.fr",
                       "BS_ALLOWED_SENDERS": allowed, "BS_SECRET_KEY": "x" * 32})
    cfg = load_config()
    return cfg, Store(cfg.scans_dir, cfg.cache_dir)


def test_import_and_delete():
    with tempfile.TemporaryDirectory() as tmp:
        cfg, store = setup(tmp)
        now = time.time()
        fake = FakeImap({
            "INBOX": {1: (now - 60, make_mail(pages=2)), 2: (now - 25 * 3600, make_mail())},
            "Sent": {7: (now - 30 * 3600, b"old"), 8: (now - 60, b"recent")},
        })
        mailer._connect_imap = lambda _cfg: fake
        worker = mailer.MailWorker(cfg, store)
        assert worker.check_mailbox() == 1
        scans = store.all()
        assert len(scans) == 1 and scans[0].pages == 2
        assert abs(scans[0].expires_at - (now - 60 + 24 * 3600)) < 5
        assert fake.folders["INBOX"] == {}, "les e-mails doivent être supprimés"
        assert list(fake.folders["Sent"]) == [8], "copies envoyées de plus de 24 h supprimées"


def test_allowed_senders_and_dedup():
    with tempfile.TemporaryDirectory() as tmp:
        cfg, store = setup(tmp, allowed="printer@remividon.fr")
        now = time.time()
        fake = FakeImap({"INBOX": {1: (now, make_mail(sender="spam@evil.test")), 2: (now, make_mail(msgid="<a@b>"))}})
        mailer._connect_imap = lambda _cfg: fake
        worker = mailer.MailWorker(cfg, store)
        assert worker.check_mailbox() == 1
        assert list(fake.folders["INBOX"]) == [1], "expéditeur inconnu : laissé (purge à 24 h)"
        fake.folders["INBOX"][3] = (now, make_mail(msgid="<a@b>"))
        assert worker.check_mailbox() == 0, "pas de doublon"


def test_expiry_and_merge():
    with tempfile.TemporaryDirectory() as tmp:
        _, store = setup(tmp)
        now = time.time()
        a = store.add(make_pdf(1), kind="scan", filename="a.pdf", created_at=now, expires_at=now + 100)
        b = store.add(make_pdf(3), kind="scan", filename="b.pdf", created_at=now, expires_at=now - 1)
        assert store.get(b.id) is None
        merged = pdftools.merge([store.pdf_path(a.id).read_bytes(), make_pdf(2)])
        assert pdftools.inspect(merged)["pages"] == 3
        store.purge_expired()
        assert not store.pdf_path(b.id).exists() and not store.thumb_path(b.id).parent.exists()
        assert store.pdf_path(a.id).exists()


def test_pin_and_sessions():
    stored = hash_pin("une phrase très longue avec des espaces 🙂")
    assert check_pin("une phrase très longue avec des espaces 🙂", stored)
    assert not check_pin("1234", stored)
    with tempfile.TemporaryDirectory() as tmp:
        s = Settings(Path(tmp) / "s.json")
        s.set_pin("1")
        token = auth.make_token("k", s.pin_hash, 1)
        assert auth.check_token(token, "k", s.pin_hash)
        s.set_pin("2")
        assert not auth.check_token(token, "k", s.pin_hash), "changer le PIN invalide les sessions"
    t = auth.Throttle()
    for _ in range(4):
        assert t.failure("ip") == 0
    assert t.failure("ip") == 30 and t.retry_after("ip") > 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
