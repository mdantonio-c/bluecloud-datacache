import json
from pathlib import Path
from typing import List

import requests
from bluecloud.endpoints.schemas import DownloadType
from restapi.connectors.celery import CeleryExt
from restapi.exceptions import NotFound
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log

DOWNLOAD_HEADERS = {
    "User-Agent": "BlueCloud DataCache HTTP-APIs",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
}


@CeleryExt.task()
def make_order(
    self: CeleryExt.TaskType,
    request_id: str,
    marine_id: str,
    order_number: str,
    downloads: List[DownloadType],
) -> str:

    path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

    # it is expected to be created by the endpoint
    if not path.exists():
        raise NotFound(str(path))

    cache = path.joinpath("cache")
    logs = path.joinpath("logs")

    cache.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)

    log.info("Task ID: {}", self.request.id)
    log.info("Request ID = {}", request_id)
    log.info("Marine ID = {}", marine_id)
    log.info("Order number = {}", order_number)
    log.info("Download list = {}", downloads[0:10])

    response = {"request_id": request_id, "order_number": order_number, "errors": []}
    for d in downloads:
        download_url = d["url"]
        filename = d["filename"]

        log.info(download_url)
        log.info(filename)
        log.info(d["order_line"])

        try:

            r = requests.get(
                download_url,
                stream=True,
                verify=False,
                headers=DOWNLOAD_HEADERS,
            )

            local_path = cache.joinpath(filename)

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

        except requests.exceptions.ConnectionError as e:
            log.error(str(e))
            log.critical("ErrorCodes.UNREACHABLE_DOWNLOAD_PATH")
            continue
        except requests.exceptions.MissingSchema as e:
            log.error(str(e))
            log.critical("ErrorCodes.UNREACHABLE_DOWNLOAD_PATH")
            continue
        except BaseException as e:
            log.error(str(e))
            log.critical("ErrorCodes.UNKNOWN_DOWNLOAD_ERROR")
            continue

        if r.status_code != 200:
            log.critical("ErrorCodes.UNREACHABLE_DOWNLOAD_PATH")
            continue

    log.info("Task executed!")

    with open(logs.joinpath("response.json"), "w+") as f:
        f.write(json.dumps(response))

    return "Task executed!"
