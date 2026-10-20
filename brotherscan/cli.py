"""Commandes d'administration : python -m brotherscan.cli <commande>."""

from __future__ import annotations

import argparse
import getpass
import sys

from .config import load_config
from .settings import Settings


def _read_pin() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\r\n")
    while True:
        pin = getpass.getpass("Nouveau code PIN : ")
        if not pin:
            print("Le code ne peut pas être vide.")
            continue
        if getpass.getpass("Confirmez le code : ") == pin:
            return pin
        print("Les deux codes ne correspondent pas, recommencez.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brotherscan")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("set-pin", help="Définir ou changer le code PIN")
    sub.add_parser("has-pin", help="Code de sortie 0 si un PIN est défini")
    sub.add_parser("check-mail", help="Tester les connexions IMAP et SMTP")
    sub.add_parser("purge", help="Supprimer immédiatement les documents expirés")
    args = parser.parse_args(argv)

    cfg = load_config()
    settings = Settings(cfg.data_dir / "settings.json")

    if args.command == "set-pin":
        pin = _read_pin()
        if not pin:
            print("Code PIN vide : rien n'a été modifié.", file=sys.stderr)
            return 1
        settings.set_pin(pin)
        print("Code PIN enregistré.")
        return 0
    if args.command == "has-pin":
        return 0 if settings.has_pin else 1
    if args.command == "check-mail":
        from .mailer import test_connections

        ok = True
        for name, success, detail in test_connections(cfg):
            ok &= success
            print(f"  {'✔' if success else '✘'} {name} : {detail}")
        return 0 if ok else 1
    if args.command == "purge":
        from .store import Store

        removed = Store(cfg.scans_dir, cfg.cache_dir).purge_expired()
        print(f"{removed} document(s) supprimé(s).")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
