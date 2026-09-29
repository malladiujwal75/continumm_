import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.config import Settings
from app.db import Database
from app.memory_service import MemoryService
from app.repository import CustomerRepository, TicketRepository
from tests.fake_hindsight import FakeHindsight


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def db(test_settings) -> Database:
    return Database(test_settings.db_path)


@pytest.fixture
def customers_repo(db) -> CustomerRepository:
    return CustomerRepository(db)


@pytest.fixture
def tickets_repo(db) -> TicketRepository:
    return TicketRepository(db)


@pytest.fixture
def fake_client() -> FakeHindsight:
    return FakeHindsight()


@pytest.fixture
def memory(fake_client, test_settings) -> MemoryService:
    return MemoryService(fake_client, test_settings)
