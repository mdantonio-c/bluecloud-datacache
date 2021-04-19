from pathlib import Path

# from typing import Any, Dict, Optional, Type, TypeVar
from faker import Faker
from flask import Flask
from restapi.services.uploader import Uploader
from restapi.tests import BaseTests

TASK_NAME = "make_order"


class TestApp(BaseTests):
    def test_task(self, app: Flask, faker: Faker) -> None:

        request_id = faker.pyint()
        marine_id = faker.pystr()
        order_number = faker.pystr()

        response = BaseTests.send_task(
            app, TASK_NAME, request_id, marine_id, order_number, [], True
        )
        assert response is None

        mail = BaseTests.read_mock_email()

        headers = mail.get("headers")
        assert headers is not None
        assert f"Task {TASK_NAME} failed" in headers

        body = mail.get("body")
        assert body is not None
        assert "NotFound" in body
        assert f"{marine_id}/{order_number}" in body

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))
        path.mkdir(parents=True)

        response = BaseTests.send_task(
            app, TASK_NAME, request_id, marine_id, order_number, [], True
        )

        assert response is not None

        assert "request_id" in response
        assert response["request_id"] == request_id

        assert "order_number" in response
        assert response["order_number"] == order_number

        assert "errors" in response
        assert len(response["errors"]) == 0

        # Nothing to be download => no errors and no zip output
        assert not Path(path.joinpath("output.zip")).exists()
