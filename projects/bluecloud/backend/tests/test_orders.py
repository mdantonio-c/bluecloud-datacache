import json
from typing import Any, Dict

from faker import Faker
from restapi.tests import API_URI, BaseTests, FlaskClient


class TestApp(BaseTests):
    def test_order_endpoint_definition(self, client: FlaskClient) -> None:

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

    def test_order_creation(self, client: FlaskClient, fake: Faker) -> None:
        headers, _ = self.do_login(client, None, None)

        # #############################################################
        # Empty input
        data: Dict[str, Any] = {}
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" in response
        assert response["request_id"] == ["Missing data for required field."]
        assert "marine_id" in response
        assert response["marine_id"] == ["Missing data for required field."]
        assert "order_number" in response
        assert response["order_number"] == ["Missing data for required field."]
        assert "downloads" in response
        assert response["downloads"] == ["Missing data for required field."]

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
        assert response["downloads"] == ["Not a valid list."]

        # #############################################################
        # Empty downloads list

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": [],
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert response["downloads"] == ["Missing data for required field."]

        # #############################################################
        # Wrong data in download list

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": json.dumps([{}]),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "0" in response["downloads"]
        assert "url" in response["downloads"]["0"]
        assert "filename" in response["downloads"]["0"]
        assert "order_line" in response["downloads"]["0"]
        assert response["downloads"]["0"]["url"] == ["Missing data for required field."]
        assert response["downloads"]["0"]["filename"] == [
            "Missing data for required field."
        ]
        assert response["downloads"]["0"]["order_line"] == [
            "Missing data for required field."
        ]

        data = {
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": json.dumps(
                [
                    {
                        "url": fake.pystr(),
                        "filename": fake.pyint(),
                        "order_line": fake.pyint(),
                    }
                ]
            ),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "0" in response["downloads"]
        assert "url" in response["downloads"]["0"]
        assert "filename" in response["downloads"]["0"]
        assert "order_line" in response["downloads"]["0"]
        assert response["downloads"]["0"]["url"] == ["Not a valid URL."]
        assert response["downloads"]["0"]["filename"] == ["Not a valid string."]
        assert response["downloads"]["0"]["order_line"] == ["Not a valid string."]

        # #############################################################
        data = {
            "debug": True,
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": json.dumps(
                [
                    {
                        "url": "https://www.google.com",
                        "filename": fake.file_name(),
                        "order_line": fake.pystr(),
                    },
                    {
                        "url": fake.pystr(),
                        "filename": fake.pyint(),
                        "order_line": fake.pyint(),
                    },
                ]
            ),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 400
        response = self.get_content(r)
        assert "request_id" not in response
        assert "marine_id" not in response
        assert "order_number" not in response
        assert "downloads" in response
        assert "0" not in response["downloads"]
        assert "1" in response["downloads"]
        assert "url" in response["downloads"]["1"]
        assert "filename" in response["downloads"]["1"]
        assert "order_line" in response["downloads"]["1"]
        assert response["downloads"]["1"]["url"] == ["Not a valid URL."]
        assert response["downloads"]["1"]["filename"] == ["Not a valid string."]
        assert response["downloads"]["1"]["order_line"] == ["Not a valid string."]

        data = {
            "debug": True,
            "request_id": fake.pystr(),
            "marine_id": fake.pystr(),
            "order_number": fake.pystr(),
            "downloads": json.dumps(
                [
                    {
                        "url": "https://www.google.com",
                        "filename": fake.file_name(),
                        "order_line": fake.pystr(),
                    },
                    {
                        "url": "https://www.google.com",
                        "filename": fake.file_name(),
                        "order_line": fake.pystr(),
                    },
                ]
            ),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 200
        self.get_content(r) == "Debug mode enabled"

    def test_order_deletion(self, client: FlaskClient, fake: Faker) -> None:

        headers, _ = self.do_login(client, None, None)

        # Not implemented yet
        r = client.delete(f"{API_URI}/order/invalid", headers=headers)
        assert r.status_code == 204
