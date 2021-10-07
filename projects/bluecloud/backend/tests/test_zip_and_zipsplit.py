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


# Please note that MAX_ZIP_SIZE is fixed to 262144 during tests


class TestApp(BaseTests):
    def test_empty_folder(self, faker: Faker) -> None:
        # Make an archive from an empty folder

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=0)

    def test_one_small_file(self, faker: Faker) -> None:
        # Make an archive from one file

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        f1 = cache.joinpath(faker.pystr())
        create_file(f1, size=1024)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=1)

    def test_two_small_files(self, faker: Faker) -> None:
        # Make an archive from two files

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        f1 = cache.joinpath(faker.pystr())
        f2 = cache.joinpath(faker.pystr())
        create_file(f1, size=1024)
        create_file(f2, size=1024)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0
        verify_zip(z, num_files=2)

    def test_two_large_files(self, faker: Faker) -> None:
        # Make an archive larger then max size => enable split

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")
        HALF_SIZE = math.ceil(MAX_ZIP_SIZE / 2)

        f3 = cache.joinpath(faker.pystr())
        f4 = cache.joinpath(faker.pystr())

        create_file(f3, size=HALF_SIZE)
        create_file(f4, size=HALF_SIZE)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 2
        assert not z.exists()
        z1 = path.joinpath("output1.zip")
        z2 = path.joinpath("output2.zip")
        verify_zip(z1, num_files=1)
        verify_zip(z2, num_files=1)

    def test_four_large_files(self, faker: Faker) -> None:
        # Make an archive with even more files

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")
        HALF_SIZE = math.ceil(MAX_ZIP_SIZE / 2)

        f3 = cache.joinpath(faker.pystr())
        f4 = cache.joinpath(faker.pystr())
        f5 = cache.joinpath(faker.pystr())
        f6 = cache.joinpath(faker.pystr())

        create_file(f3, size=HALF_SIZE)
        create_file(f4, size=HALF_SIZE)
        create_file(f5, size=HALF_SIZE)
        create_file(f6, size=HALF_SIZE)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 4
        assert not z.exists()
        z1 = path.joinpath("output1.zip")
        z2 = path.joinpath("output2.zip")
        z3 = path.joinpath("output3.zip")
        z4 = path.joinpath("output4.zip")
        verify_zip(z1, num_files=1)
        verify_zip(z2, num_files=1)
        verify_zip(z3, num_files=1)
        verify_zip(z4, num_files=1)

    def test_a_too_large_file_and_four_large_files(self, faker: Faker) -> None:
        # Make an archive with a file larger than the MAX ZIP SIZE

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")
        HALF_SIZE = math.ceil(MAX_ZIP_SIZE / 2)

        f3 = cache.joinpath(faker.pystr())
        f4 = cache.joinpath(faker.pystr())
        f5 = cache.joinpath(faker.pystr())
        f6 = cache.joinpath(faker.pystr())
        f7 = cache.joinpath(faker.pystr())

        create_file(f3, size=HALF_SIZE)
        create_file(f4, size=HALF_SIZE)
        create_file(f5, size=HALF_SIZE)
        create_file(f6, size=HALF_SIZE)
        create_file(f7, size=MAX_ZIP_SIZE * 2)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 5
        assert not z.exists()
        z1 = path.joinpath("output1.zip")
        z2 = path.joinpath("output2.zip")
        z3 = path.joinpath("output3.zip")
        z4 = path.joinpath("output4.zip")
        # This last zip will contains the too-large file
        z5 = path.joinpath("output5.zip")
        verify_zip(z1, num_files=1)
        verify_zip(z2, num_files=1)
        verify_zip(z3, num_files=1)
        verify_zip(z4, num_files=1)
        verify_zip(z5, num_files=1)

        assert z1.stat().st_size < MAX_ZIP_SIZE
        assert z2.stat().st_size < MAX_ZIP_SIZE
        assert z3.stat().st_size < MAX_ZIP_SIZE
        assert z4.stat().st_size < MAX_ZIP_SIZE
        # Please note that z5 is larger than MAX_ZIP_SIZE
        assert z5.stat().st_size > MAX_ZIP_SIZE

    def test_a_too_large_file_and_a_large_file(self, faker: Faker) -> None:
        # Make an archive with a file larger than the MAX ZIP SIZE + 1 large file

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")
        HALF_SIZE = math.ceil(MAX_ZIP_SIZE / 2)

        f6 = cache.joinpath(faker.pystr())
        f7 = cache.joinpath(faker.pystr())

        create_file(f6, size=HALF_SIZE)
        create_file(f7, size=MAX_ZIP_SIZE * 2)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 2
        assert not z.exists()
        z1 = path.joinpath("output1.zip")
        # This zip contains the too-large file
        z2 = path.joinpath("output2.zip")
        verify_zip(z1, num_files=1)
        verify_zip(z2, num_files=1)

        assert z1.stat().st_size < MAX_ZIP_SIZE
        # Please note that z2 is larger than MAX_ZIP_SIZE
        assert z2.stat().st_size > MAX_ZIP_SIZE

    def test_a_too_large_file_only(self, faker: Faker) -> None:
        # Test the case of only one oversize file
        # In this case output.zip will be empty and should be replaced

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")

        f7 = cache.joinpath(faker.pystr())

        create_file(f7, size=MAX_ZIP_SIZE * 2)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 0

        # This is output.zip without any index and contains the too large file
        verify_zip(z, num_files=1)

        # Please note that z is larger than MAX_ZIP_SIZE
        assert z.stat().st_size > MAX_ZIP_SIZE

    def test_two_too_large_files(self, faker: Faker) -> None:
        # Test the case of two oversize file
        # In this case output.zip will be empty and should be removed
        # The the two oversize files will be compressed in output1 and output2

        path = Path(tempfile.gettempdir(), faker.pystr())
        # zip filename without .zip extension
        zip_file = path.joinpath("output")
        cache = path.joinpath("cache")

        path.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)

        MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")

        f7 = cache.joinpath(faker.pystr())
        f8 = cache.joinpath(faker.pystr())

        create_file(f7, size=MAX_ZIP_SIZE * 2)
        create_file(f8, size=MAX_ZIP_SIZE * 2)

        z, chunks = make_zip_archives(path, zip_file, cache)

        assert z == zip_file.with_suffix(".zip")
        assert len(chunks) == 2
        assert not z.exists()
        z1 = path.joinpath("output1.zip")
        z2 = path.joinpath("output2.zip")
        verify_zip(z1, num_files=1)
        verify_zip(z2, num_files=1)
        # Please note that both are larger than MAX_ZIP_SIZE
        assert z1.stat().st_size > MAX_ZIP_SIZE
        assert z2.stat().st_size > MAX_ZIP_SIZE
