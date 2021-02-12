from typing import Any, Dict

from faker import Faker
from restapi.tests import API_URI, BaseTests, FlaskClient


class TestApp(BaseTests):
    def test_orders(self, client: FlaskClient, fake: Faker) -> None:

        r = client.get(f"{API_URI}/order")
        assert r.status_code == 405

        r = client.put(f"{API_URI}/order")
        assert r.status_code == 405

        r = client.delete(f"{API_URI}/order")
        assert r.status_code == 405

        r = client.post(f"{API_URI}/order")
        assert r.status_code == 401

        r = client.delete(f"{API_URI}/order/invalid")
        assert r.status_code == 401

        headers, _ = self.do_login(client, None, None)

        # #############################################################
        # Empty input
        data: Dict[str, Any] = {}
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" in response
        assert "marine_id" in response
        assert "order_number" in response
        assert "downloads" in response

        # #############################################################
        # Wrong types
        data = {
            "request_id": fake.pyint(),
            "marine_id": fake.pyint(),
            "order_number": fake.pyint(),
            "downloads": fake.pystr(),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert response["downloads"] == "Not a valid list."

        # #############################################################
        # Empty downloads list

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": [],
        }
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response

        # #############################################################
        # Wrong data in download list

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": [{}],
        }
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "url" in response
        assert "filename" in response
        assert "order_line" in response

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": [
                {
                    "url": fake.pystr(),
                    "filename": fake.pyint(),
                    "order_line": fake.pyint(),
                }
            ],
        }
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "url" in response
        assert "filename" in response
        assert "order_line" in response

        # #############################################################
        data = {
            "debug": True,
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": [
                {
                    "url": "https://www.google.com",
                    "filename": fake.filename(),
                    "order_line": fake.pystr(),
                },
                {
                    "url": "https://www.google.com",
                    "filename": fake.filename(),
                    "order_line": fake.pystr(),
                },
            ],
        }
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "url" in response
        assert "filename" in response
        assert "order_line" in response

        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 200
        self.get_content(r) == "Debug mode enabled"
