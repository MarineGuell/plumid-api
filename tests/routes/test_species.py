# api/tests/routes/test_species.py
from fastapi.testclient import TestClient


def test_create_species(client: TestClient):
    response = client.post(
        "/species",
        json={
            "species_name": "TestBird",
            "region": "TestingRegion",
            "environment": "Forest",
            "sex": "Male",
            "information": "A test bird"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["species_name"] == "TestBird"
    assert "idspecies" in data


def test_get_species(client: TestClient):
    # Assuming ID 1 exists because it was created the line before
    # (Since these tests run sequentially under the same session if using module-level db override)
    response = client.get("/species/1")
    assert response.status_code == 200
    assert response.json()["species_name"] == "TestBird"


def test_delete_species(client: TestClient):
    response = client.delete("/species/1")
    assert response.status_code == 204

    # Verify it was deleted
    get_resp = client.get("/species/1")
    assert get_resp.status_code == 404
