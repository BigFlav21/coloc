"""Gestion des colocataires en ligne de commande.

    python -m app.seed add Flav [--pin 1234]
    python -m app.seed reset Flav [--pin 1234]
    python -m app.seed list

Sans --pin, un PIN temporaire à 4 chiffres est généré et affiché une seule fois.
Le colocataire doit en choisir un nouveau à sa première connexion.
"""
import argparse
import secrets
import sys

from sqlmodel import Session, select

from .auth import PIN_RE, hash_pin
from .config import Settings
from .db import init_db, make_engine
from .models import User

PALETTE = ["#d9622b", "#7a5cc4", "#2f8f9d", "#c4487a", "#5a8f2f", "#b8862b", "#3b6fc4"]


def temp_pin() -> str:
    return f"{secrets.randbelow(10000):04d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("add", "reset"):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("--pin")
    sub.add_parser("list")
    args = parser.parse_args(argv)

    engine = make_engine(Settings().database_url)
    init_db(engine)
    with Session(engine) as db:
        if args.cmd == "list":
            for u in db.exec(select(User).order_by(User.id)):
                print(f"{u.id}\t{u.name}\t{'PIN à changer' if u.must_change_pin else 'ok'}")
            return 0

        pin = args.pin or temp_pin()
        if not PIN_RE.match(pin):
            print("Le PIN doit faire 4 à 6 chiffres.", file=sys.stderr)
            return 1
        existing = db.exec(select(User).where(User.name == args.name)).first()

        if args.cmd == "add":
            if existing:
                print(f"{args.name} existe déjà (utilise 'reset').", file=sys.stderr)
                return 1
            count = len(db.exec(select(User)).all())
            db.add(User(name=args.name, color=PALETTE[count % len(PALETTE)], pin_hash=hash_pin(pin)))
        else:
            if not existing:
                print(f"{args.name} n'existe pas.", file=sys.stderr)
                return 1
            existing.pin_hash = hash_pin(pin)
            existing.must_change_pin = True
            db.add(existing)
        db.commit()
        print(f"{args.name} : PIN temporaire {pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
