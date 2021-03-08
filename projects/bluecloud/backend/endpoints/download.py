from pathlib import Path
from typing import Dict, List

from restapi import decorators
from restapi.exceptions import NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class DownloadURLs(Schema):
    urls = fields.List(fields.URL())


class Download(EndpointResource):

    labels = ["download"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/download/<token>", summary="Download a file", responses={"200": "..."}
    )
    def get(self, token: str) -> Response:

        # validate the token
        # send the file content

        return self.response("")

    @decorators.auth.require()
    @decorators.marshal_with(DownloadURLs, code=200)
    @decorators.endpoint(
        path="/download/<marine_id>/<order_number>",
        summary="Request a download url for an order",
        responses={"200": "Download URL(s) returned"},
    )
    def post(self, marine_id: str, order_number: str) -> Response:

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))
        log.info("Create a new order in {}", path)

        if not path.exists():
            raise NotFound(
                f"Order {order_number} does not exists for marine id {marine_id}"
            )

        # invalidate previously created urls for this order

        # create one or more urls and get back as response

        data: Dict[str, List[str]] = {"urls": []}
        return self.response(data)
