import json
import os
import random
import sys
import time
import zipfile
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
# host = "https://data-dev.bluecloud.cineca.it"
r = requests.post(
    f"{host}/auth/login", data={"username": username, "password": password}
)
token = r.json()
headers = {"Authorization": f"Bearer {token}"}

rand = random.SystemRandom()

marine_ids = [
    "mattia",
]

marine_id = rand.choice(marine_ids)
order_number = faker.pystr()


def print_response_or_exit(response: requests.Response):
    log.info(response.json())

    if response.status_code >= 300:
        log.error("Status code = {}", response.status_code)
        sys.exit(1)
    log.info("Status code = {}", response.status_code)


data = {
    "marine_id": marine_id,
    "order_number": order_number,
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

print_response_or_exit(resp)

time.sleep(5)

# Send a second other to be merged
data = {
    "marine_id": marine_id,
    "order_number": order_number,
    "request_id": faker.pystr(),
    "downloads": json.dumps(
        [
            {
                "url": "https://github.com/rapydo/do/archive/v1.0.zip",
                "filename": faker.file_name(),
                "order_line": faker.pystr(),
            }
        ]
    ),
    "debug": True,
}
resp = requests.post(f"{host}/api/order", headers=headers, data=data)

print_response_or_exit(resp)

time.sleep(5)

resp = requests.get(f"{host}/api/download/{marine_id}/{order_number}", headers=headers)

print_response_or_exit(resp)

url = resp.json()["urls"][0]

log.info("Download url = {}", url)

resp = requests.get(url)

download_filename = f"{order_number}.zip"
cmd = ' curl {} --header "Authorization: Bearer {}" --output {} -O -J -L'.format(
    url, token, download_filename
)
os.system(cmd)

if os.path.isfile(download_filename):
    log.info("File downloaded")
    try:
        with zipfile.ZipFile(download_filename, "r") as myzip:
            errors = myzip.testzip()
            if errors:
                log.error("Wrong entry in the zipfile: {}", errors)
                sys.exit(1)

        log.info("Zip file verified")

    except zipfile.BadZipFile as e:
        log.error(e)
        sys.exit(1)

    os.remove(download_filename)

else:
    log.error("Warning: the download test-file has not been downloaded")

requests.get(f"{host}/auth/logout", headers=headers)
