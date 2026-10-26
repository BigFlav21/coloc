from sqlmodel import Session, select

from .models import User


def users_by_id(db: Session) -> dict[int, User]:
    return {u.id: u for u in db.exec(select(User))}
