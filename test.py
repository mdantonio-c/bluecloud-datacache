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

projectrc = load_yaml_file(PROJECTRC, is_optional=True)

variables = glom(projectrc, "project_configuration.variables.env")
faker = Faker()

host = os.environ.get("TEST_HOST", "http://localhost:8080")
username = os.environ.get("TEST_USERNAME", variables.get("AUTH_DEFAULT_USERNAME"))
password = os.environ.get("TEST_PASSWORD", variables.get("AUTH_DEFAULT_PASSWORD"))

print(f"TESTING: {host}")

# If local MAX_ZIP_SIZE is expected to be 300000
is_local = host == "http://localhost:8080"
r = requests.post(
    f"{host}/auth/login", data={"username": username, "password": password}
)
token = r.json()
headers = {"Authorization": f"Bearer {token}"}

rand = random.SystemRandom()

marine_ids = [
    "test",
]

marine_id = rand.choice(marine_ids)
order_number = faker.pystr()

log.info("Marine ID = {}", marine_id)
log.info("Order number = {}", order_number)


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

resp = requests.get(f"{host}/api/download/{marine_id}/{order_number}", headers=headers)

# Here a single url is expected
print_response_or_exit(resp)

content = resp.json()

assert len(content["urls"]) == 1

expected_size = content["urls"][0]["size"]
url = content["urls"][0]["url"]

log.info("Download url = {}", url)


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

# Here two urls are expected
print_response_or_exit(resp)

content = resp.json()

if is_local:
    assert len(content["urls"]) == 2
else:
    assert len(content["urls"]) == 1

expected_size = content["urls"][0]["size"]
url = content["urls"][0]["url"]

log.info("Download url = {}", url)

resp = requests.get(url)

download_filename = Path(f"{order_number}.zip")
cmd = ' curl {} --header "Authorization: Bearer {}" --output {} -O -J -L'.format(
    url, token, download_filename
)
os.system(cmd)

if download_filename.is_file():
    log.info("File downloaded")

    zipsize = Path(download_filename).stat().st_size
    if zipsize != expected_size:
        log.error("Wrong zip size, expected {}, found {}", expected_size, zipsize)

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

    download_filename.unlink()

else:
    log.error("Warning: the download test-file has not been downloaded")

requests.get(f"{host}/auth/logout", headers=headers)
