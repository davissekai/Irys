import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import api


class ApiContractsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_health_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_export_db_validation(self):
        response = self.client.post("/export-db", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Missing eventName or rows in payload")

    @patch("api.db_utils.save_to_db")
    def test_export_db_success(self, mock_save):
        mock_save.return_value = {
            "success": True,
            "message": "Saved",
            "export_id": "exp-1",
            "rows_inserted": 1,
        }
        response = self.client.post(
            "/export-db",
            json={"eventName": "Test Event", "rows": [{"name": "Ada"}]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["export_id"], "exp-1")
        self.assertEqual(data["rows_inserted"], 1)

    @patch("api.db_utils.list_exports")
    def test_list_exports_success(self, mock_list):
        mock_list.return_value = [
            {"export_id": "exp-1", "exported_at": "2026-02-13T12:00:00Z", "row_count": 2}
        ]
        response = self.client.get("/exports/Test%20Event")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["exports"][0]["export_id"], "exp-1")

    @patch("api.db_utils.get_export_rows")
    def test_get_export_rows_success(self, mock_rows):
        mock_rows.return_value = [{"name": "Ada", "phone": "123"}]
        response = self.client.get("/exports/Test%20Event/exp-1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rowCount"], 1)
        self.assertEqual(data["rows"][0]["name"], "Ada")


if __name__ == "__main__":
    unittest.main()
