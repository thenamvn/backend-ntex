from typing import Generator
from sqlmodel import Session
from .db.database import engine


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request is complete.
    """
    with Session(engine) as session:
        yield session
