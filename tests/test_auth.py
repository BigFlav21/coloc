from app.auth import LoginLimiter, hash_pin, verify_pin
from app.models import User

from .conftest import login, make_client


def test_hash_and_verify():
    stored = hash_pin("1234")
    assert stored != "1234"
    assert verify_pin("1234", stored)
    assert not verify_pin("1235", stored)
    assert not verify_pin("1234", "garbage")


def test_limiter_blocks_then_expires():
    now = [0.0]
    limiter = LoginLimiter(max_attempts=3, window=100, clock=lambda: now[0])
    for _ in range(3):
        assert limiter.blocked_for("a") == 0
        limiter.fail("a")
    assert limiter.blocked_for("a") > 0
    assert limiter.blocked_for("b") == 0
    now[0] = 101
    assert limiter.blocked_for("a") == 0


def test_unauthenticated_redirects_to_login(app):
    c = make_client(app)
    for path in ("/", "/menus", "/courses", "/idees"):
        r = c.get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login"


def test_htmx_unauthenticated_gets_hx_redirect(app):
    r = make_client(app).get("/calendar", headers={"HX-Request": "true"})
    assert r.status_code == 200 and r.headers["HX-Redirect"] == "/login"


def test_login_page_lists_users(app):
    r = make_client(app).get("/login")
    assert r.status_code == 200
    assert "Flav" in r.text and "Léa" in r.text


def test_wrong_pin_then_lockout(app, db):
    c = make_client(app)
    for _ in range(5):
        assert login(c, db, "Flav", "0000").status_code == 401
    assert login(c, db, "Flav", "1234").status_code == 429  # même le bon PIN est refusé
    assert login(make_client(app), db, "Léa").status_code == 303  # les autres ne sont pas touchés


def test_login_ok_gives_access(client):
    assert client.get("/").status_code == 200


def test_logout(client):
    assert client.post("/logout").status_code == 303
    assert client.get("/").status_code == 303


def test_first_login_forces_pin_change(app, db):
    user = db.query(User).filter(User.name == "Hugo").one()
    user.must_change_pin = True
    db.add(user)
    db.commit()

    c = make_client(app)
    r = login(c, db, "Hugo")
    assert r.headers["location"] == "/pin"
    assert c.get("/").headers["location"] == "/pin"  # l'app reste verrouillée
    assert c.get("/menus").headers["location"] == "/pin"

    r = c.post("/pin", data={"current": "3456", "new": "9999", "confirm": "9999"})
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert c.get("/").status_code == 200

    c2 = make_client(app)
    assert login(c2, db, "Hugo", "3456").status_code == 401
    assert login(c2, db, "Hugo", "9999").status_code == 303


def test_pin_change_validation(client):
    bad = [
        {"current": "0000", "new": "5555", "confirm": "5555"},  # mauvais PIN actuel
        {"current": "1234", "new": "12", "confirm": "12"},  # trop court
        {"current": "1234", "new": "abcd", "confirm": "abcd"},  # pas des chiffres
        {"current": "1234", "new": "5555", "confirm": "5556"},  # confirmation différente
        {"current": "1234", "new": "1234", "confirm": "1234"},  # identique
    ]
    for data in bad:
        assert client.post("/pin", data=data).status_code in (400, 401)


def test_foreign_origin_is_rejected(client):
    r = client.post("/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    r = client.post("/logout", headers={"Origin": "http://testserver"})
    assert r.status_code == 303
