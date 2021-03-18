from pathlib import Path
from typing import List

from bluecloud.endpoints.schemas import DownloadType, OrderInputSchema
from restapi import decorators
from restapi.connectors import celery
from restapi.exceptions import Conflict
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class TaskID(Schema):
    task_id = fields.Str()


class Order(EndpointResource):

    labels = ["orders"]

    @decorators.auth.require()
    @decorators.marshal_with(TaskID, code=200)
    @decorators.use_kwargs(OrderInputSchema)
    @decorators.endpoint(
        path="/order",
        summary="Create a new order by providing a list of URLs",
        responses={
            202: "Order creation accepted. Operation ID is returned",
            409: "Order already exists for the given marine id",
        },
    )
    def post(
        self,
        request_id: str,
        marine_id: str,
        order_number: str,
        downloads: List[DownloadType],
        debug: bool,
    ) -> Response:

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))
        log.info("Create a new order in {}", path)

        if path.exists():
            raise Conflict(
                f"Order {order_number} already exists for marine id {marine_id}"
            )

        path.mkdir()

        log.info("Launch a celery task to download urls in the marine_id folder")

        celery_ext = celery.get_instance()
        task = celery_ext.celery_app.send_task(
            "make_order", args=[request_id, marine_id, order_number, downloads]
        )

        return self.response({"task_id": task.id})

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<uuid>",
        summary="Delete an order",
        responses={"204": "Order successfully deleted"},
    )
    def delete(self, uuid: str) -> Response:

        log.info("Order {} to be deleted", uuid)

        return self.empty_response()
