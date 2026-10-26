from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..auth import PIN_RE, hash_pin, session_user, verify_pin
from ..db import get_session
from ..models import User
from ..templating import render

router = APIRouter()


def _login_page(request: Request, db: Session, selected: int | None = None, error: str | None = None, status: int = 200):
    users = db.exec(select(User).order_by(User.id)).all()
    return render(request, "login.html", status_code=status, users=users, selected=selected, error=error, bare=True)


@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_session)):
    if request.session.get("uid") and db.get(User, request.session["uid"]):
        return RedirectResponse("/", status_code=303)
    return _login_page(request, db)


@router.post("/login")
def login(request: Request, user_id: int = Form(...), pin: str = Form(""), db: Session = Depends(get_session)):
    user = db.get(User, user_id)
    if user is None:
        return _login_page(request, db, error="Choisis ton prénom.", status=400)

    limiter = request.app.state.limiter
    key = f"login:{user.name.lower()}"
    wait = limiter.blocked_for(key)
    if wait:
        return _login_page(request, db, user.id, f"Trop d'essais. Réessaie dans {wait // 60 + 1} minutes.", 429)

    if not verify_pin(pin, user.pin_hash):
        limiter.fail(key)
        return _login_page(request, db, user.id, "PIN incorrect.", 401)

    limiter.reset(key)
    request.session.clear()
    request.session["uid"] = user.id
    return RedirectResponse("/pin" if user.must_change_pin else "/", status_code=303)


@router.get("/pin")
def pin_form(request: Request, user: User = Depends(session_user)):
    return render(request, "pin.html", user=user, first=user.must_change_pin, bare=user.must_change_pin)


@router.post("/pin")
def pin_change(
    request: Request,
    current: str = Form(""),
    new: str = Form(""),
    confirm: str = Form(""),
    user: User = Depends(session_user),
    db: Session = Depends(get_session),
):
    def page(error: str, status: int = 400):
        return render(request, "pin.html", status_code=status, user=user, first=user.must_change_pin,
                      bare=user.must_change_pin, error=error)

    limiter = request.app.state.limiter
    key = f"pin:{user.name.lower()}"
    if limiter.blocked_for(key):
        return page("Trop d'essais. Réessaie plus tard.", 429)
    if not verify_pin(current, user.pin_hash):
        limiter.fail(key)
        return page("Le PIN actuel est incorrect.", 401)
    if not PIN_RE.match(new):
        return page("Le nouveau PIN doit faire 4 à 6 chiffres.")
    if new != confirm:
        return page("Les deux PIN ne correspondent pas.")
    if new == current:
        return page("Choisis un PIN différent de l'actuel.")

    limiter.reset(key)
    user.pin_hash = hash_pin(new)
    user.must_change_pin = False
    db.add(user)
    db.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
