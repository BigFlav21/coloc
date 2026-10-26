import datetime as dt

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str = "#d9622b"
    pin_hash: str
    must_change_pin: bool = True

    @property
    def initial(self) -> str:
        return self.name[:1].upper()


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str
    title: str
    day: dt.date = Field(index=True)
    start: dt.time | None = None
    details: str = ""
    author_id: int = Field(foreign_key="user.id")


class EventRsvp(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)
    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    user_id: int = Field(foreign_key="user.id")
    status: str  # yes | no


class Meal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    day: dt.date = Field(unique=True, index=True)
    dish: str
    cook_id: int | None = Field(default=None, foreign_key="user.id")


class MealPresence(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("meal_id", "user_id"),)
    id: int | None = Field(default=None, primary_key=True)
    meal_id: int = Field(foreign_key="meal.id", index=True)
    user_id: int = Field(foreign_key="user.id")
    status: str  # yes | no


class ShoppingItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    qty: str = ""
    category: str = "Autre"
    added_by: int = Field(foreign_key="user.id")
    checked: bool = False
    checked_by: int | None = Field(default=None, foreign_key="user.id")


class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    category: str = "Autre"
    author_id: int = Field(foreign_key="user.id")


class IdeaVote(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("idea_id", "user_id"),)
    id: int | None = Field(default=None, primary_key=True)
    idea_id: int = Field(foreign_key="idea.id", index=True)
    user_id: int = Field(foreign_key="user.id")
