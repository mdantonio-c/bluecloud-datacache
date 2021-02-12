from typing import List, TypedDict

from restapi import decorators
from restapi.config import TESTING
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.utilities.logs import log


class DownloadType(TypedDict):
    url: str
    filename: str
    order_line: str


class Download(Schema):
    # download url to get the data
    url = fields.Url(required=True)
    # the new filename for the datafile
    filename = fields.Str(required=True)
    # unique number for identification
    order_line = fields.Str(required=True)


class OrderInputSchema(Schema):
    # Unique Id number for debugging and communication
    request_id = fields.Str(required=True)
    # Unique ID to identify the web-site user
    marine_id = fields.Str(required=True)
    # Unique order number
    order_number = fields.Str(required=True)
    # List of downloads
    downloads = fields.List(fields.Nested(Download), required=True)
    # Used to test the endpoint without call back Maris
    # During tests is automatically defaulted to True ( === TESTING)
    debug = fields.Boolean(missing=TESTING)


class Order(EndpointResource):

    labels = ["order"]

    @decorators.auth.require()
    @decorators.use_kwargs(OrderInputSchema)
    @decorators.endpoint(
        path="/order",
        summary="Create a new order by providing a list of URLs",
        responses={"202": "Order creation accepted"},
    )
    def post(
        self,
        request_id: str,
        marine_id: str,
        order_number: str,
        downloads: List[DownloadType],
        debug: bool,
    ) -> Response:

        log.info("Create a new order")

        log.info("Launch a celery task to download urls in the marine_id folder")

        # Assign with the uuid of newly created resource
        if debug:
            task_id = "Debug mode enabled"
        else:
            task_id = "..."

        return self.response(task_id)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<uuid>",
        summary="Delete an order",
        responses={"204": "Order successfully deleted"},
    )
    def delete(self, uuid: str) -> Response:

        log.info("Order {} to be deleted", uuid)

        return self.empty_response()
