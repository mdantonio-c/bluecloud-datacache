import os
from pathlib import Path

from cryptography.fernet import Fernet
from restapi.config import APP_SECRETS, UPLOAD_PATH
from restapi.exceptions import BadRequest
from restapi.services.authentication import import_secret


def get_seed_path(abs_order_path: Path) -> Path:
    return abs_order_path.joinpath(".seed")


def get_seed(abs_order_path: Path) -> str:
    return import_secret(get_seed_path(abs_order_path))[0:12].decode()


def get_secret() -> bytes:
    return import_secret(APP_SECRETS.joinpath("order_secrets.key"))


def get_token(abs_order_path: Path, relative_zip_path: str) -> str:

    secret = get_secret()
    fernet = Fernet(secret)

    seed = get_seed(abs_order_path)
    plain = f"{seed}:{relative_zip_path}"

    return fernet.encrypt(plain.encode()).decode()


def read_token(cypher: str) -> str:
    secret = get_secret()
    fernet = Fernet(secret)

    # This is seed:marine_id/order_number/filefile
    plain = fernet.decrypt(cypher.encode()).decode().split(":")

    # This is seed
    seed = plain[0]

    # This is marine_id/order_number/filefile
    zip_filepath = plain[1]

    # This is marine_id/order_number
    zip_path = os.path.dirname(zip_filepath)

    # marine_id and order_number split by /
    marine_id, order_number = zip_path.split("/")

    abs_zip_path = UPLOAD_PATH.joinpath(marine_id, order_number)

    expected_seed = get_seed(abs_zip_path)

    if seed != expected_seed:
        raise BadRequest("Invalid token seed")

    return zip_filepath
