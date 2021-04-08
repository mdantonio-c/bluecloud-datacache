import json
import time
import zipfile
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Optional, Type, TypeVar

import pytest
from faker import Faker
from restapi.services.uploader import Uploader
from restapi.tests import API_URI, BaseTests, FlaskClient

T = TypeVar("T", bound="TemporaryRemovePath")


# This is a copy from submodules/do, not available in http-api
class TemporaryRemovePath:
    def __init__(self, path: Path):
        self.path = path.absolute()
        self.tmp_path = self.path.with_suffix(f"{path.suffix}.bak")

    def __enter__(self: T) -> T:

        self.path.rename(self.tmp_path)
        return self

    def __exit__(
        self,
        _type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> bool:
        self.tmp_path.rename(self.path)
        # return False if the exception is not handled:
        # -> return True if the exception is None (nothing to be handled)
        # -> return False if the exception is not None (because it is not handled here)
        # always return False is not accepted by mypy...
        return _type is None


def download_and_verify_zip(
    client: FlaskClient, faker: Faker, download_url: str
) -> None:
    # http:// or https://
    assert download_url.startswith("http")
    assert "/api/download/" in download_url

    r = client.get(f"{API_URI}/download/invalidtoken")
    assert r.status_code == 400

    r = client.get(download_url)
    assert r.status_code == 200

    local_filename = f"{faker.pystr()}.zip"
    with open(local_filename, "wb+") as f:
        f.write(r.data)

    try:
        with zipfile.ZipFile(local_filename, "r") as myzip:
            errors = myzip.testzip()
            assert errors is None

    except zipfile.BadZipFile as e:  # pragma: no cover
        pytest.fail(str(e))


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

        # This url is not defined
        r = client.delete(f"{API_URI}/order/invalid")
        assert r.status_code == 404

        r = client.delete(f"{API_URI}/order/invalid/invalid")
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
        self.save("marine_id", marine_id)
        order_number = faker.pystr()
        self.save("order_number", order_number)
        request_id = faker.pystr()

        filename_1 = faker.file_name()
        filename_2 = faker.file_name()
        filename_3 = faker.file_name()

        order_line1 = faker.pystr()
        order_line2 = faker.pystr()
        order_line3 = faker.pystr()

        download_url1 = "https://www.google.com"
        download_url2 = "https://github.com/rapydo/http-api/archive/v1.0.zip"
        download_url3 = "https://invalidurlafailisexpected.zzz/f.zip"

        data = {
            "debug": True,
            "request_id": request_id,
            "marine_id": marine_id,
            "order_number": order_number,
            "downloads": json.dumps(
                [
                    {
                        "url": download_url1,
                        "filename": filename_1,
                        "order_line": order_line1,
                    },
                    {
                        "url": download_url2,
                        "filename": filename_2,
                        "order_line": order_line2,
                    },
                    {
                        "url": download_url3,
                        "filename": filename_3,
                        "order_line": order_line3,
                    },
                ]
            ),
        }
        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 202
        response = self.get_content(r)
        assert "request_id" in response
        assert "datetime" in response

        dt = datetime.strptime(response["datetime"], "%Y%m%dT%H:%M:%S")
        now = datetime.now()
        assert (now - dt).total_seconds() < 10

        # Not the best... but enough for now
        time.sleep(20)

        # Now the order should be completed, let's verify the result:

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

        assert path.exists()

        cache = path.joinpath("cache")
        logs = path.joinpath("logs")
        zip_file = path.joinpath("output.zip")

        assert cache.exists()
        assert logs.exists()
        assert zip_file.exists()

        zip_size = zip_file.stat().st_size
        assert zip_size > 0

        assert logs.joinpath("response.json").exists()

        assert cache.joinpath(filename_1).exists()
        assert cache.joinpath(filename_2).exists()
        assert not cache.joinpath(filename_3).exists()

        with open(logs.joinpath("response.json")) as json_file:
            response = json.load(json_file)

            assert response is not None
            assert "request_id" in response
            assert "order_number" in response
            assert "errors" in response
            assert response["request_id"] == request_id
            assert response["order_number"] == order_number
            assert isinstance(response["errors"], list)
            assert len(response["errors"]) == 1
            assert response["errors"][0]["order_line"] == order_line3
            assert response["errors"][0]["url"] == download_url3
            assert response["errors"][0]["error_number"] == "001"

        # Send a second order to be merged:
        new_request_id = faker.pystr()
        filename_4 = faker.file_name()
        order_line4 = faker.pystr()
        download_url4 = "https://github.com/rapydo/do/archive/v1.0.zip"

        data = {
            "debug": True,
            "request_id": new_request_id,
            "marine_id": marine_id,
            "order_number": order_number,
            "downloads": json.dumps(
                [
                    {
                        "url": download_url4,
                        "filename": filename_4,
                        "order_line": order_line4,
                    },
                ]
            ),
        }

        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 202
        response = self.get_content(r)
        assert "request_id" in response
        assert "datetime" in response

        # Not the best... but enough for now
        time.sleep(20)

        # Now the order should be completed, let's verify the result:

        assert path.exists()
        assert cache.exists()
        assert logs.exists()
        assert zip_file.exists()

        new_zip_size = zip_file.stat().st_size
        assert new_zip_size > 0
        assert new_zip_size > zip_size

        assert logs.joinpath("response.json").exists()

        assert cache.joinpath(filename_1).exists()
        assert cache.joinpath(filename_2).exists()
        assert not cache.joinpath(filename_3).exists()
        assert cache.joinpath(filename_4).exists()

        # response.json file is overwritten
        with open(logs.joinpath("response.json")) as json_file:
            response = json.load(json_file)

            assert response is not None
            assert "request_id" in response
            assert "order_number" in response
            assert "errors" in response
            assert response["request_id"] == new_request_id
            assert response["order_number"] == order_number
            assert isinstance(response["errors"], list)
            assert len(response["errors"]) == 0

        # This is to test concurrency (not really handled yet)
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
                        "url": download_url1,
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                    {
                        "url": download_url2,
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                ]
            ),
        }

        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 202

        data = {
            "debug": True,
            "request_id": faker.pystr(),
            "marine_id": marine_id,
            "order_number": order_number,
            "downloads": json.dumps(
                [
                    {
                        "url": download_url4,
                        "filename": faker.file_name(),
                        "order_line": faker.pystr(),
                    },
                ]
            ),
        }

        r = client.post(f"{API_URI}/order", headers=headers, data=data)
        assert r.status_code == 202

        # Not the best... but enough for now
        time.sleep(20)

        # This order is created by merging exactly the same file of the first order
        # but not sequentially, i.e. with concurrent jobs
        # Expected zip size is exactly the size of the first
        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

        assert path.exists()
        zip_file = path.joinpath("output.zip")
        assert zip_file.exists()

        concurrent_zip_size = zip_file.stat().st_size
        assert concurrent_zip_size > 0
        assert concurrent_zip_size > new_zip_size

    def test_download_endpoint_definition(self, client: FlaskClient) -> None:

        r = client.get(f"{API_URI}/download")
        assert r.status_code == 404

        r = client.put(f"{API_URI}/download")
        assert r.status_code == 404

        r = client.post(f"{API_URI}/download")
        assert r.status_code == 404

        r = client.delete(f"{API_URI}/download")
        assert r.status_code == 404

        r = client.get(f"{API_URI}/download/token")
        assert r.status_code == 400

        r = client.put(f"{API_URI}/download/token")
        assert r.status_code == 405

        r = client.post(f"{API_URI}/download/token")
        assert r.status_code == 405

        r = client.delete(f"{API_URI}/download/token")
        assert r.status_code == 405

        r = client.get(f"{API_URI}/download/marine_id/order_number")
        assert r.status_code == 401

        r = client.put(f"{API_URI}/download/marine_id/order_number")
        assert r.status_code == 405

        r = client.post(f"{API_URI}/download/marine_id/order_number")
        assert r.status_code == 405

        r = client.delete(f"{API_URI}/download/marine_id/order_number")
        assert r.status_code == 405

    def test_order_download(self, client: FlaskClient, faker: Faker) -> None:

        headers, _ = self.do_login(client, None, None)
        marine_id = self.get("marine_id")
        order_number = self.get("order_number")

        r = client.get(f"{API_URI}/download/invalid/invalid", headers=headers)
        assert r.status_code == 404

        r = client.get(f"{API_URI}/download/{marine_id}/invalid", headers=headers)
        assert r.status_code == 404

        r = client.get(f"{API_URI}/download/invalid/{order_number}", headers=headers)
        assert r.status_code == 404

        # Request download links:
        r = client.get(
            f"{API_URI}/download/{marine_id}/{order_number}", headers=headers
        )
        assert r.status_code == 200

        response = self.get_content(r)
        assert "urls" in response
        assert isinstance(response["urls"], list)

        assert len(response["urls"]) == 1

        download_url = response["urls"][0]

        download_and_verify_zip(client, faker, download_url)

        # Request a new download link:
        r = client.get(
            f"{API_URI}/download/{marine_id}/{order_number}", headers=headers
        )
        assert r.status_code == 200

        response = self.get_content(r)
        assert "urls" in response
        assert isinstance(response["urls"], list)

        assert len(response["urls"]) == 1

        new_download_url = response["urls"][0]

        download_and_verify_zip(client, faker, new_download_url)

        assert new_download_url != download_url

        r = client.get(new_download_url)
        assert r.status_code == 200

        r = client.get(download_url)
        assert r.status_code == 400

    def test_order_deletion(self, client: FlaskClient, faker: Faker) -> None:

        headers, _ = self.do_login(client, None, None)
        marine_id = self.get("marine_id")
        order_number = self.get("order_number")

        r = client.delete(f"{API_URI}/order/invalid/invalid", headers=headers)
        assert r.status_code == 404

        r = client.get(
            f"{API_URI}/download/{marine_id}/{order_number}", headers=headers
        )
        assert r.status_code == 200

        response = self.get_content(r)
        assert "urls" in response
        assert isinstance(response["urls"], list)

        assert len(response["urls"]) == 1

        download_url = response["urls"][0]
        r = client.get(download_url)
        assert r.status_code == 200

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

        assert path.exists()

        # Test error if the zip file does not exist (but the order still exist...
        # so this is an error condition that should never occur)
        with TemporaryRemovePath(path.joinpath("output.zip")):
            r = client.get(download_url)
            assert r.status_code == 400
        r = client.get(download_url)
        assert r.status_code == 200

        r = client.delete(
            f"{API_URI}/order/{marine_id}/{order_number}", headers=headers
        )
        assert r.status_code == 204

        assert not path.exists()

        r = client.get(download_url)
        assert r.status_code == 400
