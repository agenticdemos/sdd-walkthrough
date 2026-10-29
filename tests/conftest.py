import pytest
from fastapi.testclient import TestClient

from ledger.api import create_app
from ledger.store import Store


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def client(store):
    return TestClient(create_app(store))
