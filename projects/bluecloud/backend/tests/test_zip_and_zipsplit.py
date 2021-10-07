import math
import os
import tempfile
import zipfile
from pathlib import Path

import pytest
from bluecloud.tasks.make_order import make_zip_archives
from faker import Faker
from restapi.env import Env
from restapi.tests import BaseTests

TASK_NAME = "make_order"


def verify_zip(z: Path, num_files: int = 0) -> None:
    assert z.exists()

    try:
        with zipfile.ZipFile(z, "r") as myzip:
            errors = myzip.testzip()
            assert errors is None

            assert len(myzip.infolist()) == num_files
    except zipfile.BadZipFile as e:  # pragma: no cover
        pytest.fail(str(e))


def create_file(file: Path, size: int = 1024) -> Path:
    with open(file, "wb") as f:
        f.write(os.urandom(size))
    return file


class TestApp(BaseTests):
    def test_zip_and_zipsplit(self, faker: Faker) -> None:
        # Please note that MAX_ZIP_SIZE is fixed to 204800 during tests

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        # 1 - Make an archive from an empty folder
        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=0)

        # 2 - Make an archive from two files
        f1 = cache.joinpath(faker.pystr())
        f2 = cache.joinpath(faker.pystr())
        create_file(f1, size=1024)
        create_file(f2, size=1024)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=2)

        # 3 - Make an archive from one file (previos - one deleted)
        f1.unlink()
        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=1)

        # 4 - Make an archive larger then max size => enable split
        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")
        HALF_SIZE = math.ceil(MAX_ZIP_SIZE / 2)

        f3 = cache.joinpath(faker.pystr())
        f4 = cache.joinpath(faker.pystr())

        create_file(f3, size=HALF_SIZE)
        create_file(f4, size=HALF_SIZE)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 2
        verify_zip(z, num_files=4)
        z1 = cache.joinpath("output1.zip")
        z2 = cache.joinpath("output2.zip")
        verify_zip(z1, num_files=2)
        verify_zip(z2, num_files=2)

        # 5 - Make an archive with even more files
        f5 = cache.joinpath(faker.pystr())
        f6 = cache.joinpath(faker.pystr())

        create_file(f5, size=HALF_SIZE)
        create_file(f6, size=HALF_SIZE)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 4
        verify_zip(z, num_files=5)
        z1 = cache.joinpath("output1.zip")
        z2 = cache.joinpath("output2.zip")
        z3 = cache.joinpath("output3.zip")
        z4 = cache.joinpath("output4.zip")
        verify_zip(z1, num_files=2)
        verify_zip(z2, num_files=1)
        verify_zip(z3, num_files=1)
        verify_zip(z4, num_files=1)

        # 6 - Make an archive with a file larger than the MAX ZIP SIZE
        f7 = cache.joinpath(faker.pystr())

        create_file(f7, size=MAX_ZIP_SIZE * 2)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 5
        verify_zip(z, num_files=6)
        z1 = cache.joinpath("output1.zip")
        z2 = cache.joinpath("output2.zip")
        z3 = cache.joinpath("output3.zip")
        z4 = cache.joinpath("output4.zip")
        z5 = cache.joinpath("output4.zip")
        verify_zip(z1, num_files=2)
        verify_zip(z2, num_files=1)
        verify_zip(z3, num_files=1)
        verify_zip(z4, num_files=1)
        verify_zip(z5, num_files=1)

        assert z1.stat().st_size < MAX_ZIP_SIZE
        assert z2.stat().st_size < MAX_ZIP_SIZE
        assert z3.stat().st_size < MAX_ZIP_SIZE
        assert z4.stat().st_size < MAX_ZIP_SIZE
        assert z5.stat().st_size > MAX_ZIP_SIZE
