import os
from pathlib import Path

from cryptography.fernet import Fernet
from restapi.config import APP_SECRETS
from restapi.exceptions import BadRequest
from restapi.services.authentication import import_secret
from restapi.services.uploader import Uploader


def get_seed(abs_zip_path: Path) -> str:
    return import_secret(abs_zip_path.joinpath(".seed"))[0:12].decode()


def get_secret() -> bytes:
    return import_secret(APP_SECRETS.joinpath("order_secrets.key"))


def get_token(abs_zip_path: Path, zip_path: str) -> str:

    secret = get_secret()
    fernet = Fernet(secret)

    seed = get_seed(abs_zip_path)
    plain = f"{seed}:{zip_path}"

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

    # This is /uploads/marine_id/order_number
    abs_zip_path = Uploader.absolute_upload_file(
        order_number, subfolder=Path(marine_id)
    )

    expected_seed = get_seed(abs_zip_path)

    if seed != expected_seed:
        raise BadRequest("Invalid token seed")

    return zip_filepath
