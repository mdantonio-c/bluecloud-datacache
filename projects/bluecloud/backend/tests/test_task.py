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

        # Send a request with a wrong / missing path
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

        # Send a request with zero files to be downloaded
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

        # Send a request with two files to be downloaded (one with an invalid url)

        wrong_download_url_1 = "https://invalidurlafailisexpected.zzz/f.zip"
        wrong_order_line_1 = faker.pystr()

        downloads = [
            {
                "url": "https://github.com/rapydo/http-api/archive/v1.0.zip",
                "filename": faker.file_name(),
                "order_line": faker.pystr(),
            },
            {
                "url": wrong_download_url_1,
                "filename": faker.file_name(),
                "order_line": wrong_order_line_1,
            },
        ]

        response = BaseTests.send_task(
            app, TASK_NAME, request_id, marine_id, order_number, downloads, True
        )

        assert response is not None

        assert "request_id" in response
        assert response["request_id"] == request_id

        assert "order_number" in response
        assert response["order_number"] == order_number

        assert "errors" in response
        assert len(response["errors"]) == 1

        assert "url" in response["errors"][0]
        assert response["errors"][0]["url"] == wrong_download_url_1

        assert "order_line" in response["errors"][0]
        assert response["errors"][0]["order_line"] == wrong_order_line_1

        assert "error_number" in response["errors"][0]
        assert response["errors"][0]["error_number"] == "001"

        assert Path(path.joinpath("output.zip")).exists()