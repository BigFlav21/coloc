from dataclasses import dataclass

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..auth import current_user
from ..db import get_session
from ..models import Idea, IdeaVote, User
from ..queries import users_by_id
from ..templating import render

router = APIRouter(prefix="/idees")

CATEGORIES = ["Soirée", "Sortie", "Autre"]


@dataclass
class IdeaView:
    idea: Idea
    author: User | None
    votes: int
    voted: bool
    is_author: bool


def idea_view(db: Session, idea: Idea, user: User) -> IdeaView:
    votes = db.exec(select(IdeaVote).where(IdeaVote.idea_id == idea.id)).all()
    return IdeaView(
        idea=idea,
        author=db.get(User, idea.author_id),
        votes=len(votes),
        voted=any(v.user_id == user.id for v in votes),
        is_author=idea.author_id == user.id,
    )


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_session)):
    views = [idea_view(db, i, user) for i in db.exec(select(Idea))]
    views.sort(key=lambda v: (-v.votes, -v.idea.id))
    return render(request, "ideas.html", user=user, active="idees", ideas=views, categories=CATEGORIES)


@router.post("")
def add(
    title: str = Form(""),
    category: str = Form("Autre"),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    title = title.strip()
    if not (1 <= len(title) <= 100) or category not in CATEGORIES:
        raise HTTPException(400, "Idée invalide")
    db.add(Idea(title=title, category=category, author_id=user.id))
    db.commit()
    return RedirectResponse("/idees", status_code=303)


def _get(db: Session, idea_id: int) -> Idea:
    idea = db.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404)
    return idea


@router.post("/{idea_id}/vote", response_class=HTMLResponse)
def vote(idea_id: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_session)):
    idea = _get(db, idea_id)
    existing = db.exec(select(IdeaVote).where(IdeaVote.idea_id == idea.id, IdeaVote.user_id == user.id)).first()
    if existing:
        db.delete(existing)
    else:
        db.add(IdeaVote(idea_id=idea.id, user_id=user.id))
    db.commit()
    return render(request, "partials/idea.html", user=user, v=idea_view(db, idea, user))


@router.post("/{idea_id}/delete", response_class=HTMLResponse)
def delete(idea_id: int, user: User = Depends(current_user), db: Session = Depends(get_session)):
    idea = _get(db, idea_id)
    if idea.author_id != user.id:
        raise HTTPException(403, "Seul l'auteur peut supprimer")
    for v in db.exec(select(IdeaVote).where(IdeaVote.idea_id == idea.id)):
        db.delete(v)
    db.delete(idea)
    db.commit()
    return HTMLResponse("")
