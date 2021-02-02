from typing import List
from restapi import decorators
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.utilities.logs import log


class OrderInputSchema(Schema):
    marine_id = fields.Str(required=True)
    urls = fields.List(fields.URL(), required=True)


class Order(EndpointResource):

    labels = ["order"]

    @decorators.auth.require()
    @decorators.use_kwargs(OrderInputSchema)
    @decorators.endpoint(
        path="/order",
        summary="Create a new order by providing a list of URLs",
        responses={
            "202": "Order creation accepted"
        }
    )
    def post(self, marine_id: str, urls: List[str]) -> Response:

        log.info("Create a new order")

        log.info("Launch a celery task to download urls in the marine_id folder")

        # Assign with the uuid of newly created resource
        data = {}

        return self.response(data)

    @decorators.auth.require()
    @decorators.endpoint(
        path="/order/<uuid>",
        summary="Delete an order",
        responses={
            "204": "Order successfully deleted"
        }
    )
    def delete(self, uuid: str) -> Response:

        log.info("Order {} to be deleted", uuid)

        return self.empty_response()
