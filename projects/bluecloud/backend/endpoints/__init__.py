import os
from pathlib import Path

from cryptography.fernet import Fernet
from restapi.config import APP_SECRETS
from restapi.exceptions import BadRequest
from restapi.services.authentication import import_secret


def get_seed(zip_path: str) -> bytes:
    return import_secret(Path(zip_path).joinpath(".seed"))[0:12]


def get_secret() -> bytes:
    return import_secret(APP_SECRETS.joinpath("order_secrets.key"))


def get_token(zip_path: str, zip_name: str) -> str:

    secret = get_secret()
    fernet = Fernet(secret)

    seed = get_seed(zip_path)
    plain = f"{seed}{os.path.join(zip_path, zip_name)}"

    return fernet.encrypt(plain.encode()).decode()


def read_token(cypher: str) -> str:
    secret = get_secret()
    fernet = Fernet(secret)

    # This is seed:zippath/filefile
    plain = fernet.decrypt(cypher.encode()).decode().split(":")
    seed = plain[0]
    zip_filepath = plain[1]
    zip_path = os.path.dirname(zip_filepath)
    expected_seed = get_seed(zip_path)

    if seed != expected_seed:
        raise BadRequest("Invalid token seed")

    return zip_filepath
