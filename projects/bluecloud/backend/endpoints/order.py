import shutil
from datetime import datetime
from typing import List

from bluecloud.endpoints.schemas import DownloadType, OrderInputSchema
from restapi import decorators
from restapi.config import DATA_PATH
from restapi.connectors import celery
from restapi.exceptions import Conflict, NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.authentication import User
from restapi.utilities.logs import log


class OrdersList(Schema):
    orders = fields.List(fields.Str())


class TaskID(Schema):
    request_id = fields.Str()
    datetime = fields.DateTime(format="%Y%m%dT%H:%M:%S")


class Orders(EndpointResource):

    labels = ["orders"]

    @decorators.auth.require()
    @decorators.marshal_with(OrdersList, code=200)
    @decorators.endpoint(
        path="/orders",
        summary="List all defined orders",
        responses={200: "List of orders is returned"},
    )
    def get(self, user: User) -> Response:

        orders: List[str] = []

        for p in DATA_PATH.glob("*/*"):
            # marine_id = p.parent.name
            order_number = p.name
            orders.append(order_number)
        return self.response({"orders": orders})


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

        close_file = path.joinpath("closed")
        if close_file.exists():
            raise Conflict(f"Order {order_number} is closed")

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

        log.info("Order to be deleted: {} on MarineID {}", order_number, marine_id)

        shutil.rmtree(path)

        log.info("Order {} deleted", order_number)

        return self.empty_response()

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<marine_id>/<order_number>",
        summary="Close an order",
        responses={
            204: "Order successfully closed",
            404: "Order not found",
            409: "Order already closed",
        },
    )
    def patch(self, marine_id: str, order_number: str, user: User) -> Response:
        """
        NOTE: if you ever want to implement a re-open endpint:
            1 - de-compress all zip files into cache folder
            2 - delete the closed file
        """
        path = DATA_PATH.joinpath(marine_id, order_number)

        if not path.exists():
            raise NotFound(
                f"Order {order_number} does not exist for marine id {marine_id}"
            )

        log.info("Order to be closed: {} on MarineID {}", order_number, marine_id)

        close_file = path.joinpath("closed")
        if close_file.exists():
            raise Conflict(f"Order {order_number} is already closed")

        # clean the cache
        cache = path.joinpath("cache")
        if cache.exists():
            for f in cache.iterdir():
                if f.is_file():
                    log.info("Removing {}", f.resolve())
                    f.unlink()

        cache_oversize = path.joinpath("cache_oversize")
        if cache_oversize.exists():
            for f in cache_oversize.iterdir():
                if f.is_file():
                    log.info("Removing {}", f.resolve())
                    f.unlink()

        close_file.touch()
        log.info("Order {} closed", order_number)

        return self.empty_response()
