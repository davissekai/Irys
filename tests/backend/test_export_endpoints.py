from fastapi.testclient import TestClient

import api


client = TestClient(api.app)


def test_export_db_missing_payload():
    response = client.post("/export-db", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing eventName or rows in payload"


def test_export_db_success(monkeypatch):
    def fake_save_to_db(event_name, rows, export_id=None):
        return {
            "success": True,
            "message": f"Saved {len(rows)} rows",
            "table_name": "test_event",
            "export_id": export_id or "generated-id",
            "rows_inserted": len(rows),
        }

    monkeypatch.setattr(api.db_utils, "save_to_db", fake_save_to_db)

    payload = {"eventName": "Test Event", "rows": [{"name": "A"}]}
    response = client.post("/export-db", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rows_inserted"] == 1
    assert "export_id" in data


def test_list_exports_success(monkeypatch):
    expected = [
        {"export_id": "exp-1", "exported_at": "2026-02-13T10:00:00Z", "row_count": 4},
        {"export_id": "exp-2", "exported_at": "2026-02-12T10:00:00Z", "row_count": 2},
    ]
    monkeypatch.setattr(api.db_utils, "list_exports", lambda event_name: expected)

    response = client.get("/exports/Test%20Event")
    assert response.status_code == 200
    data = response.json()
    assert data["eventName"] == "Test Event"
    assert data["exports"] == expected


def test_get_export_rows_success(monkeypatch):
    expected_rows = [{"name": "A", "phone": "123"}, {"name": "B", "phone": "999"}]
    monkeypatch.setattr(api.db_utils, "get_export_rows", lambda event_name, export_id: expected_rows)

    response = client.get("/exports/Test%20Event/exp-1")
    assert response.status_code == 200
    data = response.json()
    assert data["eventName"] == "Test Event"
    assert data["exportId"] == "exp-1"
    assert data["rowCount"] == 2
    assert data["rows"] == expected_rows


def test_list_exports_bad_request(monkeypatch):
    def raise_value_error(_):
        raise ValueError("Invalid event name.")

    monkeypatch.setattr(api.db_utils, "list_exports", raise_value_error)
    response = client.get("/exports/!!!")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid event name."


def test_get_export_rows_server_error(monkeypatch):
    def raise_runtime_error(_event_name, _export_id):
        raise RuntimeError("db offline")

    monkeypatch.setattr(api.db_utils, "get_export_rows", raise_runtime_error)
    response = client.get("/exports/Test%20Event/exp-1")
    assert response.status_code == 500
    assert response.json()["detail"] == "db offline"
