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

    def test_order_creation(self, client: FlaskClient, faker: Faker) -> None:
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
            "request_id": faker.pyint(),
            "marine_id": faker.pyint(),
            "order_number": faker.pyint(),
            "downloads": faker.pystr(),
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
            "request_id": faker.pystr(),
            "marine_id": faker.pystr(),
            "order_number": faker.pystr(),
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
            "request_id": faker.pystr(),
            "marine_id": faker.pystr(),
            "order_number": faker.pystr(),
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
            "request_id": faker.pystr(),
            "marine_id": faker.pystr(),
            "order_number": faker.pystr(),
            "downloads": json.dumps(
                [
                    {
                        "url": faker.pystr(),
                        "filename": faker.pyint(),
                        "order_line": faker.pyint(),
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
            "request_id": faker.pystr(),
            "marine_id": faker.pystr(),
            "order_number": faker.pystr(),
            "downloads": json.dumps(
                [
                    {
                        "url": "https://www.google.com",
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                    {
                        "url": faker.pystr(),
                        "filename": faker.pyint(),
                        "order_line": faker.pyint(),
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

        marine_id = faker.pystr()
        order_number = faker.pystr()
        data = {
            "debug": True,
            "request_id": faker.pystr(),
            "marine_id": marine_id,
            "order_number": order_number,
            "downloads": json.dumps(
                [
                    {
                        "url": "https://www.google.com",
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                    {
                        "url": "https://www.google.com",
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                ]
            ),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 200
        # assert self.get_content(r) == the uuid of the celery task

        # The order already exists
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 409
        error = f"Order {order_number} already exists for marine id {marine_id}"
        assert self.get_content(r) == error

    def test_order_deletion(self, client: FlaskClient, faker: Faker) -> None:

        headers, _ = self.do_login(client, None, None)

        # Not implemented yet
        r = client.delete(f"{API_URI}/order/invalid", headers=headers)
        assert r.status_code == 204
