from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..auth import current_user
from ..db import get_session
from ..models import ShoppingItem, User
from ..queries import users_by_id
from ..templating import render

router = APIRouter(prefix="/courses")

CATEGORIES = ["Frais", "Épicerie", "Maison", "Autre"]


def _item(request: Request, db: Session, item: ShoppingItem, user: User):
    return render(request, "partials/item.html", user=user, i=item, users=users_by_id(db))


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_session)):
    items = db.exec(select(ShoppingItem).order_by(ShoppingItem.checked, ShoppingItem.id)).all()
    groups = [(c, [i for i in items if i.category == c]) for c in CATEGORIES]
    return render(
        request, "courses.html", user=user, active="courses", categories=CATEGORIES,
        groups=[(c, its) for c, its in groups if its], users=users_by_id(db),
        checked=sum(1 for i in items if i.checked),
    )


@router.post("")
def add(
    name: str = Form(""),
    category: str = Form("Autre"),
    qty: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    name = name.strip()
    if not (1 <= len(name) <= 60) or category not in CATEGORIES:
        raise HTTPException(400, "Article invalide")
    db.add(ShoppingItem(name=name, category=category, qty=qty.strip()[:20], added_by=user.id))
    db.commit()
    return RedirectResponse("/courses", status_code=303)


@router.post("/clear")
def clear(user: User = Depends(current_user), db: Session = Depends(get_session)):
    for item in db.exec(select(ShoppingItem).where(ShoppingItem.checked == True)):  # noqa: E712
        db.delete(item)
    db.commit()
    return RedirectResponse("/courses", status_code=303)


def _get(db: Session, item_id: int) -> ShoppingItem:
    item = db.get(ShoppingItem, item_id)
    if item is None:
        raise HTTPException(404)
    return item


@router.post("/{item_id}/toggle", response_class=HTMLResponse)
def toggle(item_id: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_session)):
    item = _get(db, item_id)
    item.checked = not item.checked
    item.checked_by = user.id if item.checked else None
    db.add(item)
    db.commit()
    return _item(request, db, item, user)


@router.post("/{item_id}/delete", response_class=HTMLResponse)
def delete(item_id: int, user: User = Depends(current_user), db: Session = Depends(get_session)):
    item = _get(db, item_id)
    db.delete(item)
    db.commit()
    return HTMLResponse("")
