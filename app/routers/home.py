import calendar as pycal
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, col, select

from ..auth import current_user
from ..db import get_session
from ..models import Event, EventRsvp, User
from ..queries import users_by_id
from ..templating import render, today

router = APIRouter()

EVENT_TYPES = {
    "soiree": {"label": "Soirée", "icon": "🎉", "dot": "party", "rsvp": True},
    "diner": {"label": "Dîner", "icon": "🍽", "dot": "dinner", "rsvp": True},
    "invite": {"label": "Invité", "icon": "🧳", "dot": "guest", "rsvp": False},
    "absence": {"label": "Absence", "icon": "🚪", "dot": "away", "rsvp": False},
    "autre": {"label": "Autre", "icon": "📝", "dot": "other", "rsvp": True},
}


@dataclass
class EventView:
    ev: Event
    kind: dict
    author: User | None
    yes: list[User]
    no: list[User]
    mine: str | None
    is_author: bool


def event_view(db: Session, ev: Event, user: User) -> EventView:
    users = users_by_id(db)
    rsvps = db.exec(select(EventRsvp).where(EventRsvp.event_id == ev.id)).all()
    return EventView(
        ev=ev,
        kind=EVENT_TYPES.get(ev.type, EVENT_TYPES["autre"]),
        author=users.get(ev.author_id),
        yes=[users[r.user_id] for r in rsvps if r.status == "yes" and r.user_id in users],
        no=[users[r.user_id] for r in rsvps if r.status == "no" and r.user_id in users],
        mine=next((r.status for r in rsvps if r.user_id == user.id), None),
        is_author=ev.author_id == user.id,
    )


def parse_month(value: str | None, now: dt.date) -> dt.date:
    try:
        year, month = (int(p) for p in (value or "").split("-"))
        return dt.date(year, month, 1)
    except (ValueError, TypeError):
        return now.replace(day=1)


def build_calendar(db: Session, first: dt.date, now: dt.date) -> dict:
    weeks = pycal.Calendar(0).monthdatescalendar(first.year, first.month)
    start, end = weeks[0][0], weeks[-1][-1]
    events = db.exec(select(Event).where(Event.day >= start, Event.day <= end)).all()
    dots: dict[dt.date, list[str]] = defaultdict(list)
    for ev in events:
        dot = EVENT_TYPES.get(ev.type, EVENT_TYPES["autre"])["dot"]
        if dot not in dots[ev.day]:
            dots[ev.day].append(dot)
    prev = (first - dt.timedelta(days=1)).replace(day=1)
    nxt = (first + dt.timedelta(days=31)).replace(day=1)
    return {
        "first": first,
        "prev": prev.strftime("%Y-%m"),
        "next": nxt.strftime("%Y-%m"),
        "weeks": [
            [{"day": d, "off": d.month != first.month, "today": d == now, "dots": dots[d][:3]} for d in week]
            for week in weeks
        ],
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, m: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_session)):
    now = today(request)
    first = parse_month(m, now)
    upcoming = db.exec(
        select(Event).where(Event.day >= now).order_by(Event.day, Event.start).limit(20)
    ).all()
    return render(
        request, "home.html", user=user, active="home", types=EVENT_TYPES,
        calendar=build_calendar(db, first, now),
        events=[event_view(db, ev, user) for ev in upcoming],
    )


@router.get("/calendar", response_class=HTMLResponse)
def calendar_partial(request: Request, m: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_session)):
    now = today(request)
    return render(request, "partials/calendar.html", user=user, calendar=build_calendar(db, parse_month(m, now), now))


@router.post("/events")
def create_event(
    ev_type: str = Form(..., alias="type"),
    title: str = Form(""),
    day: str = Form(""),
    start: str = Form(""),
    details: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    title = title.strip()
    if ev_type not in EVENT_TYPES or not (1 <= len(title) <= 80):
        raise HTTPException(400, "Évènement invalide")
    try:
        when = dt.date.fromisoformat(day)
        at = dt.time.fromisoformat(start) if start else None
    except ValueError:
        raise HTTPException(400, "Date ou heure invalide")
    db.add(Event(type=ev_type, title=title, day=when, start=at, details=details.strip()[:200], author_id=user.id))
    db.commit()
    return RedirectResponse(f"/?m={when:%Y-%m}", status_code=303)


def _get_event(db: Session, event_id: int) -> Event:
    ev = db.get(Event, event_id)
    if ev is None:
        raise HTTPException(404)
    return ev


@router.post("/events/{event_id}/rsvp", response_class=HTMLResponse)
def rsvp(
    event_id: int,
    request: Request,
    status: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    ev = _get_event(db, event_id)
    if status not in ("yes", "no") or not EVENT_TYPES.get(ev.type, {}).get("rsvp"):
        raise HTTPException(400, "Réponse impossible")
    existing = db.exec(select(EventRsvp).where(EventRsvp.event_id == ev.id, EventRsvp.user_id == user.id)).first()
    if existing and existing.status == status:
        db.delete(existing)  # recliquer annule la réponse
    elif existing:
        existing.status = status
        db.add(existing)
    else:
        db.add(EventRsvp(event_id=ev.id, user_id=user.id, status=status))
    db.commit()
    return render(request, "partials/event.html", user=user, v=event_view(db, ev, user))


@router.post("/events/{event_id}/delete", response_class=HTMLResponse)
def delete_event(event_id: int, user: User = Depends(current_user), db: Session = Depends(get_session)):
    ev = _get_event(db, event_id)
    if ev.author_id != user.id:
        raise HTTPException(403, "Seul l'auteur peut supprimer")
    for r in db.exec(select(EventRsvp).where(col(EventRsvp.event_id) == ev.id)):
        db.delete(r)
    db.delete(ev)
    db.commit()
    return HTMLResponse("")
