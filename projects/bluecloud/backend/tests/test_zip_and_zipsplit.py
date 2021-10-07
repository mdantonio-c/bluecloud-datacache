import tempfile
import zipfile
from pathlib import Path

import pytest
from bluecloud.tasks.make_order import make_zip_archives
from faker import Faker
from restapi.tests import BaseTests

TASK_NAME = "make_order"


def test_zip(z: Path, valid=True, num_files=0) -> None:
    assert z.exists()

    try:
        with zipfile.ZipFile(z, "r") as myzip:
            errors = myzip.testzip()

            if valid:
                assert errors is None
            else:
                assert errors is not None

            assert len(myzip.infolist) == num_files
    except zipfile.BadZipFile as e:  # pragma: no cover
        if valid:
            pytest.fail(str(e))


class TestApp(BaseTests):
    def test_zip_and_zipsplit(self, faker: Faker) -> None:
        # Please note that MAX_ZIP_SIZE is fixed to 204800 during tests

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        # Make an archive from an empty folder
        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        test_zip(z, valid=True, num_files=0)
