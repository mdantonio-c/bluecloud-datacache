from typing import List

from bluecloud.endpoints.schemas import DownloadType
from restapi.connectors.celery import CeleryExt
from restapi.utilities.logs import log


@CeleryExt.task()
def make_order(self, marine_id: str, order_number: str, downloads: List[DownloadType]):
    log.info("Task ID: {}", self.request.id)

    log.info("Marine ID = {}", marine_id)
    log.info("Order number = {}", order_number)
    log.info("Download list = {}", downloads[0:10])

    log.info("Task executed!")

    return "Task executed!"
