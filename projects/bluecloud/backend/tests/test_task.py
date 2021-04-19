# from pathlib import Path
# from typing import Any, Dict, Optional, Type, TypeVar
from faker import Faker
from flask import Flask
from restapi.tests import BaseTests

# from restapi.services.uploader import Uploader


class TestApp(BaseTests):
    def test_task(self, app: Flask, faker: Faker) -> None:

        request_id = faker.pyint()
        marine_id = faker.pystr()
        order_number = faker.pystr()
        output = BaseTests.send_task(
            app, "make_order", request_id, marine_id, order_number, [], True
        )
        assert output is None

        mail = BaseTests.read_mock_email()

        headers = mail.get("headers")
        assert headers is not None
        assert "Task test_task failed" in headers

        body = mail.get("body")
        assert body is not None
        assert "NotFound" in body
        assert f"{marine_id}/{order_number}" in body
