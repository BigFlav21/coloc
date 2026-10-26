import datetime as dt
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..auth import current_user
from ..db import get_session
from ..models import Meal, MealPresence, User
from ..queries import users_by_id
from ..templating import DAYS, MONTHS, render, today

router = APIRouter(prefix="/menus")

WINDOW_DAYS = 7


@dataclass
class MealView:
    meal: Meal
    cook: User | None
    yes: int
    mine: str | None
    is_cook: bool


def meal_view(db: Session, meal: Meal, user: User) -> MealView:
    presences = db.exec(select(MealPresence).where(MealPresence.meal_id == meal.id)).all()
    return MealView(
        meal=meal,
        cook=db.get(User, meal.cook_id) if meal.cook_id else None,
        yes=sum(1 for p in presences if p.status == "yes"),
        mine=next((p.status for p in presences if p.user_id == user.id), None),
        is_cook=meal.cook_id == user.id,
    )


def _window(now: dt.date) -> list[dt.date]:
    return [now + dt.timedelta(days=i) for i in range(WINDOW_DAYS)]


def _row(request: Request, day: dt.date, m: MealView | None, user: User):
    return render(request, "partials/meal_day.html", user=user, day=day, m=m)


@router.get("", response_class=HTMLResponse)
def page(request: Request, err: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_session)):
    now = today(request)
    days = _window(now)
    meals = {m.day: m for m in db.exec(select(Meal).where(Meal.day >= days[0], Meal.day <= days[-1]))}
    rows = [(d, meal_view(db, meals[d], user) if d in meals else None) for d in days]
    first, last = days[0], days[-1]
    return render(
        request, "menus.html", user=user, active="menus", rows=rows,
        options=[(d.isoformat(), f"{DAYS[d.weekday()].capitalize()} {d.day}") for d in days],
        span=f"{first.day} {MONTHS[first.month - 1]} au {last.day} {MONTHS[last.month - 1]}",
        error="Ce soir est déjà pris par quelqu'un d'autre." if err == "taken" else None,
    )


@router.post("")
def propose(
    request: Request,
    day: str = Form(""),
    dish: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    dish = dish.strip()
    try:
        when = dt.date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, "Date invalide")
    if when not in _window(today(request)) or not (1 <= len(dish) <= 80):
        raise HTTPException(400, "Menu invalide")
    meal = db.exec(select(Meal).where(Meal.day == when)).first()
    if meal and meal.cook_id not in (None, user.id):
        return RedirectResponse("/menus?err=taken", status_code=303)
    if meal:
        meal.dish, meal.cook_id = dish, user.id
    else:
        meal = Meal(day=when, dish=dish, cook_id=user.id)
    db.add(meal)
    db.commit()
    return RedirectResponse("/menus", status_code=303)


def _get_meal(db: Session, meal_id: int) -> Meal:
    meal = db.get(Meal, meal_id)
    if meal is None:
        raise HTTPException(404)
    return meal


@router.post("/{meal_id}/presence", response_class=HTMLResponse)
def presence(
    meal_id: int,
    request: Request,
    status: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    meal = _get_meal(db, meal_id)
    if status not in ("yes", "no"):
        raise HTTPException(400, "Réponse invalide")
    existing = db.exec(select(MealPresence).where(MealPresence.meal_id == meal.id, MealPresence.user_id == user.id)).first()
    if existing and existing.status == status:
        db.delete(existing)
    elif existing:
        existing.status = status
        db.add(existing)
    else:
        db.add(MealPresence(meal_id=meal.id, user_id=user.id, status=status))
    db.commit()
    return _row(request, meal.day, meal_view(db, meal, user), user)


@router.post("/{meal_id}/delete", response_class=HTMLResponse)
def delete(meal_id: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_session)):
    meal = _get_meal(db, meal_id)
    if meal.cook_id != user.id:
        raise HTTPException(403, "Seul le cuisinier peut supprimer")
    for p in db.exec(select(MealPresence).where(MealPresence.meal_id == meal.id)):
        db.delete(p)
    day = meal.day
    db.delete(meal)
    db.commit()
    return _row(request, day, None, user)
