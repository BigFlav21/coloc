import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import hash_pin
from app.config import Settings
from app.db import make_engine
from app.main import create_app
from app.models import User

PINS = {"Flav": "1234", "Léa": "2345", "Hugo": "3456"}


@pytest.fixture
def app():
    engine = make_engine("sqlite://")
    app = create_app(Settings(secret_key="test", database_url="sqlite://"), engine=engine)
    with Session(engine) as db:
        for name, pin in PINS.items():
            db.add(User(name=name, pin_hash=hash_pin(pin), must_change_pin=False))
        db.commit()
    return app


@pytest.fixture
def db(app):
    with Session(app.state.engine) as session:
        yield session


def make_client(app) -> TestClient:
    return TestClient(app, follow_redirects=False)


def login(client: TestClient, db: Session, name: str, pin: str | None = None):
    user = db.query(User).filter(User.name == name).one()
    return client.post("/login", data={"user_id": user.id, "pin": pin or PINS[name]})


@pytest.fixture
def client(app, db):
    c = make_client(app)
    assert login(c, db, "Flav").status_code == 303
    return c


@pytest.fixture
def other(app, db):
    """Client connecté en tant que Léa."""
    c = make_client(app)
    assert login(c, db, "Léa").status_code == 303
    return c
