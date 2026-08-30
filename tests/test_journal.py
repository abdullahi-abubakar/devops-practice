import pytest
from fastapi.testclient import TestClient

from main import app, entries

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store() -> None:
    entries.clear()
    yield
    entries.clear()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_entries_empty() -> None:
    response = client.get("/entries")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_entry() -> None:
    created = client.post(
        "/entries",
        json={"title": "Day 1", "body": "Wrote the Journal API."},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["title"] == "Day 1"
    assert data["body"] == "Wrote the Journal API."
    assert "id" in data

    fetched = client.get(f"/entries/{data['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == data["id"]


def test_update_entry() -> None:
    created = client.post(
        "/entries",
        json={"title": "Draft", "body": "Original"},
    )
    entry_id = created.json()["id"]

    updated = client.patch(f"/entries/{entry_id}", json={"title": "Published"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Published"
    assert updated.json()["body"] == "Original"


def test_delete_entry() -> None:
    created = client.post(
        "/entries",
        json={"title": "Temp", "body": "Remove me"},
    )
    entry_id = created.json()["id"]

    deleted = client.delete(f"/entries/{entry_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/entries/{entry_id}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Entry not found"
