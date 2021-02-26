from pathlib import Path
from typing import List

from bluecloud.endpoints.schemas import DownloadType
from restapi.connectors.celery import CeleryExt
from restapi.exceptions import NotFound
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


@CeleryExt.task()
def make_order(
    self, marine_id: str, order_number: str, downloads: List[DownloadType]
) -> str:

    path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

    # it is expected to be created by the endpoint
    if not path.exists():
        raise NotFound(str(path))

    with open(path.joinpath("test.success"), "w+") as f:
        f.write("success!")

    log.info("Task ID: {}", self.request.id)

    log.info("Marine ID = {}", marine_id)
    log.info("Order number = {}", order_number)
    log.info("Download list = {}", downloads[0:10])

    log.info("Task executed!")

    return "Task executed!"
