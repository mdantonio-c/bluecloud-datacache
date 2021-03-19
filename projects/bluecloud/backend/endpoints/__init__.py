from cryptography.fernet import Fernet
from restapi.config import APP_SECRETS
from restapi.services.authentication import import_secret


def get_secret() -> bytes:
    return import_secret(APP_SECRETS.joinpath("order_secrets.key"))


def get_token(plain: str) -> str:
    secret = get_secret()
    fernet = Fernet(secret)

    return fernet.encrypt(plain.encode()).decode()


def read_token(cypher: str) -> str:
    secret = get_secret()
    fernet = Fernet(secret)

    return fernet.decrypt(cypher.encode()).decode()
