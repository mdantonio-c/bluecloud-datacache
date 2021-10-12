import shutil
from datetime import datetime
from typing import List

from bluecloud.endpoints.schemas import DownloadType, OrderInputSchema
from restapi import decorators
from restapi.config import DATA_PATH
from restapi.connectors import celery
from restapi.exceptions import NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log


class TaskID(Schema):
    request_id = fields.Str()
    datetime = fields.DateTime(format="%Y%m%dT%H:%M:%S")


class Order(EndpointResource):

    labels = ["orders"]

    @decorators.auth.require()
    @decorators.marshal_with(TaskID, code=202)
    @decorators.use_kwargs(OrderInputSchema)
    @decorators.endpoint(
        path="/order",
        summary="Create a new order by providing a list of URLs",
        responses={202: "Order creation accepted. Operation ID is returned"},
    )
    def post(
        self,
        request_id: str,
        marine_id: str,
        order_number: str,
        downloads: List[DownloadType],
        debug: bool,
        user: User,
    ) -> Response:

        path = DATA_PATH.joinpath(marine_id, order_number)

        if path.exists():
            log.info("Merging order with previous data in {}", path)
        else:
            log.info("Create a new order in {}", path)
            path.mkdir(parents=True)

        celery_ext = celery.get_instance()
        task = celery_ext.celery_app.send_task(
            "make_order",
            args=(
                request_id,
                marine_id,
                order_number,
                downloads,
                debug,
            ),
        )

        return self.response(
            {"request_id": task.id, "datetime": datetime.now()}, code=202
        )

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<marine_id>/<order_number>",
        summary="Delete an order",
        responses={204: "Order successfully deleted"},
    )
    def delete(self, marine_id: str, order_number: str, user: User) -> Response:

        path = DATA_PATH.joinpath(marine_id, order_number)

        if not path.exists():
            raise NotFound(
                f"Order {order_number} does not exist for marine id {marine_id}"
            )

        log.info("Order to be deleted: {} on marineID {}", order_number, marine_id)

        shutil.rmtree(path)

        log.info("Order {} deleted", order_number)

        return self.empty_response()
