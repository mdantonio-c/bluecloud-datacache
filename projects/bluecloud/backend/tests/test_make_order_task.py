import os
import zipfile
from pathlib import Path

import pytest
from faker import Faker
from flask import Flask
from restapi.config import DATA_PATH
from restapi.connectors.celery import Ignore
from restapi.tests import BaseTests

TASK_NAME = "make_order"


class TestApp(BaseTests):
    def test_make_order_task(self, app: Flask, faker: Faker) -> None:

        request_id = faker.pyint()
        marine_id = faker.pystr()
        order_number = faker.pystr()

        # Send a request with a wrong / missing path
        with pytest.raises(Ignore):
            self.send_task(
                app, TASK_NAME, request_id, marine_id, order_number, [], True
            )

        mail = self.read_mock_email()

        headers = mail.get("headers")
        assert headers is not None
        assert f"Task {TASK_NAME} failed" in headers

        body = mail.get("body")
        assert body is not None
        assert "NotFound" in body
        assert f"{marine_id}/{order_number}" in body

        path = DATA_PATH.joinpath(marine_id, order_number)
        path.mkdir(parents=True)

        # Send a request with zero files to be downloaded
        response = self.send_task(
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

        # Unreachable
        wrong_download_url_1 = "https://invalidurlafailisexpected.zzz/f.zip"
        wrong_order_line_1 = faker.pystr()
        # Missing schema

        wrong_download_url_2 = "github.com/rapydo/http-api/archive/v1.0.zip"
        wrong_order_line_2 = faker.pystr()

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
            {
                "url": wrong_download_url_2,
                "filename": faker.file_name(),
                "order_line": wrong_order_line_2,
            },
        ]

        response = self.send_task(
            app, TASK_NAME, request_id, marine_id, order_number, downloads, True
        )

        assert response is not None

        assert "request_id" in response
        assert response["request_id"] == request_id

        assert "order_number" in response
        assert response["order_number"] == order_number

        assert "errors" in response
        assert len(response["errors"]) == 2

        assert "url" in response["errors"][0]
        assert response["errors"][0]["url"] == wrong_download_url_1

        assert "order_line" in response["errors"][0]
        assert response["errors"][0]["order_line"] == wrong_order_line_1

        assert "error_number" in response["errors"][0]
        assert response["errors"][0]["error_number"] == "001"

        assert "url" in response["errors"][1]
        assert response["errors"][1]["url"] == wrong_download_url_2

        assert "order_line" in response["errors"][1]
        assert response["errors"][1]["order_line"] == wrong_order_line_2

        assert "error_number" in response["errors"][1]
        assert response["errors"][1]["error_number"] == "001"
        assert Path(path.joinpath("output.zip")).exists()

        downloads = [
            {
                "url": "https://github.com/rapydo/http-api/archive/v1.0.zip",
                "filename": faker.file_name(),
                "order_line": faker.pystr(),
            },
        ]

        request_id = faker.pyint()
        marine_id = faker.pystr()
        order_number = faker.pystr()

        path = DATA_PATH.joinpath(marine_id, order_number)
        path.mkdir(parents=True)

        os.environ["MAX_ZIP_SIZE"] = 1024
        # send a url containing a large zip
        # Expected an output.zip containing the files, not a matrioska-zip

        response = self.send_task(
            app, TASK_NAME, request_id, marine_id, order_number, downloads, True
        )

        zippath = path.joinpath("output.zip")
        assert zippath.exists()

        local_unzipdir = path.joinpath("tmpunzippath")
        with zipfile.ZipFile(zippath, "r") as zipref:

            zipref.extractall(local_unzipdir)

            assert Path("http-api-1.0") in local_unzipdir.iterdir()
