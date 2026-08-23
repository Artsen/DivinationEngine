from collections.abc import Generator, Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


class FakeRandom:
    def __init__(self, bits: list[int] | None = None, numbers: list[int] | None = None) -> None:
        self.bits = iter(bits or [0] * 100)
        self.numbers = iter(numbers or [0] * 100)

    def sample(self, population: Sequence, count: int) -> list:
        return list(population)[:count]

    def bit(self) -> int:
        return next(self.bits)

    def randbelow(self, upper_bound: int) -> int:
        return next(self.numbers) % upper_bound


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: object, _: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient]:
    app = create_app()

    def override_session() -> Generator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.state.random_source = FakeRandom()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def collection(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/collections",
        json={
            "slug": "test-deck",
            "name": "Test Deck",
            "system_type": "oracle",
            "supports_reversals": True,
        },
    )
    assert response.status_code == 201
    collection = response.json()
    for sequence, name in enumerate(["Alpha", "Beta", "Gamma"], 1):
        item_response = client.post(
            f"/api/v1/collections/{collection['id']}/items",
            json={"slug": name.lower(), "name": name, "sequence": sequence},
        )
        assert item_response.status_code == 201
    return collection


@pytest.fixture
def reading(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/readings", json={"title": "Test reading", "question": "A test?"}
    )
    assert response.status_code == 201
    return response.json()
