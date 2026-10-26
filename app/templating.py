from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

templates = Jinja2Templates(directory=BASE_DIR / "templates")


def month_year(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}"


def dow_short(d: date) -> str:
    return DAYS[d.weekday()][:3]


def hm(t: time | None) -> str:
    return "" if t is None else f"{t.hour}h{t.minute:02d}"


templates.env.filters["month_year"] = month_year
templates.env.filters["dow"] = dow_short
templates.env.filters["hm"] = hm
templates.env.globals["DAYS"] = DAYS
templates.env.globals["MONTHS"] = MONTHS


def today(request: Request) -> date:
    return datetime.now(ZoneInfo(request.app.state.settings.timezone)).date()


def render(request: Request, name: str, status_code: int = 200, **context):
    context.setdefault("user", None)
    context.setdefault("today", today(request))
    return templates.TemplateResponse(request, name, context, status_code=status_code)
