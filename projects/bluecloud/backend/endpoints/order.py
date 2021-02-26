from typing import List

from bluecloud.endpoints.schemas import DownloadType, OrderInputSchema
from restapi import decorators
from restapi.connectors import celery
from restapi.rest.definition import EndpointResource, Response
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class Order(EndpointResource):

    labels = ["orders"]

    @decorators.auth.require()
    @decorators.use_kwargs(OrderInputSchema)
    @decorators.endpoint(
        path="/order",
        summary="Create a new order by providing a list of URLs",
        responses={
            202: "Order creation accepted. Operation ID is returned",
            409: "Order already exists",
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

        path = Uploader.absolute_upload_file(order_number, subfolder=marine_id)
        log.info("Create a new order in {}", path)

        log.info("Launch a celery task to download urls in the marine_id folder")

        celery_ext = celery.get_instance()
        task = celery_ext.celery_app.send_task(
            "make_order", args=[marine_id, order_number, downloads]
        )

        return self.response(task.id)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<uuid>",
        summary="Delete an order",
        responses={"204": "Order successfully deleted"},
    )
    def delete(self, uuid: str) -> Response:

        log.info("Order {} to be deleted", uuid)

        return self.empty_response()
