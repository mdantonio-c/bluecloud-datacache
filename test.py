import json
import random
from pathlib import Path

import requests
from controller import PROJECTRC, log
from controller.utilities.configuration import load_yaml_file
from faker import Faker
from glom import glom

projectrc = load_yaml_file(PROJECTRC, path=Path(), is_optional=True)

variables = glom(projectrc, "project_configuration.variables.env")
faker = Faker()

username = variables.get("AUTH_DEFAULT_USERNAME")
password = variables.get("AUTH_DEFAULT_PASSWORD")
host = "http://localhost:8080"
r = requests.post(
    f"{host}/auth/login", data={"username": username, "password": password}
)
token = r.json()
headers = {"Authorization": f"Bearer {token}"}

rand = random.SystemRandom()

marine_ids = [
    "my_marineid_1",
    "my_marineid_2",
    "my_marineid_3",
    "my_marineid_4",
    "my_marineid_5",
]

data = {
    "marine_id": rand.choice(marine_ids),
    "order_number": faker.pystr(),
    "request_id": faker.pystr(),
    "downloads": json.dumps(
        [
            {
                "url": "https://github.com/rapydo/http-api/archive/v1.0.zip",
                "filename": faker.file_name(),
                "order_line": faker.pystr(),
            },
            {
                "url": "https://thisisaninvalidurl.com/v1.0.zip",
                "filename": faker.file_name(),
                "order_line": faker.pystr(),
            },
        ]
    ),
    "debug": True,
}
resp = requests.post(f"{host}/api/order", headers=headers, data=data)

if resp.status_code >= 300:
    log.error("Status code = {}", resp.status_code)
else:
    log.info("Status code = {}", resp.status_code)

log.info(resp.json())

requests.get(f"{host}/auth/logout", headers=headers)
