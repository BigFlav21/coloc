import datetime as dt

from sqlmodel import select

from app.models import Event, EventRsvp, Idea, IdeaVote, Meal, MealPresence, ShoppingItem

TODAY = dt.date.today()


# --- Accueil / évènements ---------------------------------------------------

def make_event(client, **overrides):
    data = {"type": "soiree", "title": "Soirée jeux", "day": (TODAY + dt.timedelta(days=2)).isoformat(),
            "start": "20:30", "details": "Bruyant"}
    data.update(overrides)
    return client.post("/events", data=data)


def test_create_event_shows_on_home(client, db):
    r = make_event(client)
    assert r.status_code == 303
    page = client.get("/").text
    assert "Soirée jeux" in page and "Bruyant" in page and "20h30" in page
    assert db.exec(select(Event)).one().author_id is not None


def test_event_validation(client):
    assert make_event(client, type="nope").status_code == 400
    assert make_event(client, title="  ").status_code == 400
    assert make_event(client, day="pas-une-date").status_code == 400


def test_rsvp_toggle(client, db):
    make_event(client)
    ev = db.exec(select(Event)).one()
    r = client.post(f"/events/{ev.id}/rsvp", data={"status": "yes"})
    assert r.status_code == 200 and "1 oui" in r.text
    r = client.post(f"/events/{ev.id}/rsvp", data={"status": "no"})
    assert "0 oui · 1 non" in r.text
    client.post(f"/events/{ev.id}/rsvp", data={"status": "no"})  # recliquer annule
    assert db.exec(select(EventRsvp)).all() == []


def test_info_events_have_no_rsvp(client, db):
    make_event(client, type="invite", title="Max dort ici")
    ev = db.exec(select(Event)).one()
    assert client.post(f"/events/{ev.id}/rsvp", data={"status": "yes"}).status_code == 400


def test_only_author_deletes_event(client, other, db):
    make_event(client)
    ev = db.exec(select(Event)).one()
    assert other.post(f"/events/{ev.id}/delete").status_code == 403
    assert client.post(f"/events/{ev.id}/delete").status_code == 200
    assert db.exec(select(Event)).all() == []


def test_calendar_month_navigation(client):
    make_event(client, day="2026-03-15")
    r = client.get("/calendar?m=2026-03")
    assert "mars 2026" in r.text and 'class="dot party"' in r.text
    assert "m=2026-02" in r.text and "m=2026-04" in r.text  # liens précédent / suivant
    assert client.get("/calendar?m=garbage").status_code == 200  # mois invalide -> mois courant


# --- Menus ------------------------------------------------------------------

def test_menu_propose_and_conflict(client, other, db):
    day = TODAY.isoformat()
    assert client.post("/menus", data={"day": day, "dish": "Pâtes pesto"}).status_code == 303
    assert "Pâtes pesto" in client.get("/menus").text
    r = other.post("/menus", data={"day": day, "dish": "Autre chose"})
    assert r.headers["location"] == "/menus?err=taken"
    assert db.exec(select(Meal)).one().dish == "Pâtes pesto"
    client.post("/menus", data={"day": day, "dish": "Pizza"})  # le cuisinier peut modifier
    assert db.exec(select(Meal)).one().dish == "Pizza"


def test_menu_outside_window_rejected(client):
    far = (TODAY + dt.timedelta(days=30)).isoformat()
    assert client.post("/menus", data={"day": far, "dish": "Trop loin"}).status_code == 400


def test_meal_presence_and_delete(client, other, db):
    client.post("/menus", data={"day": TODAY.isoformat(), "dish": "Raclette"})
    meal = db.exec(select(Meal)).one()
    r = other.post(f"/menus/{meal.id}/presence", data={"status": "yes"})
    assert "1 🍽" in r.text
    other.post(f"/menus/{meal.id}/presence", data={"status": "yes"})
    assert db.exec(select(MealPresence)).all() == []
    assert other.post(f"/menus/{meal.id}/delete").status_code == 403
    assert client.post(f"/menus/{meal.id}/delete").status_code == 200
    assert db.exec(select(Meal)).all() == []


# --- Courses ----------------------------------------------------------------

def test_shopping_flow(client, other, db):
    client.post("/courses", data={"name": "Lait", "category": "Frais"})
    client.post("/courses", data={"name": "Pâtes", "category": "Épicerie", "qty": "x2"})
    page = other.get("/courses").text
    assert "Lait" in page and "Pâtes" in page and "x2" in page

    item = db.exec(select(ShoppingItem).where(ShoppingItem.name == "Lait")).one()
    r = other.post(f"/courses/{item.id}/toggle")
    assert "done-text" in r.text
    db.refresh(item)
    assert item.checked and item.checked_by is not None

    client.post("/courses/clear")
    assert [i.name for i in db.exec(select(ShoppingItem))] == ["Pâtes"]


def test_shopping_validation(client):
    assert client.post("/courses", data={"name": "", "category": "Frais"}).status_code == 400
    assert client.post("/courses", data={"name": "X", "category": "Inconnue"}).status_code == 400


# --- Idées ------------------------------------------------------------------

def test_ideas_vote_and_order(client, other, db):
    client.post("/idees", data={"title": "Escape game", "category": "Sortie"})
    client.post("/idees", data={"title": "Raclette", "category": "Soirée"})
    raclette = db.exec(select(Idea).where(Idea.title == "Raclette")).one()

    other.post(f"/idees/{raclette.id}/vote")
    client.post(f"/idees/{raclette.id}/vote")
    page = client.get("/idees").text
    assert page.index("Raclette") < page.index("Escape game")  # le plus voté d'abord

    r = other.post(f"/idees/{raclette.id}/vote")  # recliquer retire le vote
    assert len(db.exec(select(IdeaVote)).all()) == 1
    assert "<b>1</b>" in r.text


def test_only_author_deletes_idea(client, other, db):
    client.post("/idees", data={"title": "Karaoké", "category": "Soirée"})
    idea = db.exec(select(Idea)).one()
    assert other.post(f"/idees/{idea.id}/delete").status_code == 403
    assert client.post(f"/idees/{idea.id}/delete").status_code == 200
    assert db.exec(select(Idea)).all() == []


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_seed_cli(tmp_path, monkeypatch):
    from app import seed
    monkeypatch.setenv("COLOC_DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    assert seed.main(["add", "Tom", "--pin", "4321"]) == 0
    assert seed.main(["add", "Tom"]) == 1  # existe déjà
    assert seed.main(["add", "Bob", "--pin", "12"]) == 1  # PIN invalide
    assert seed.main(["reset", "Tom", "--pin", "1111"]) == 0
    assert seed.main(["reset", "Nobody"]) == 1
