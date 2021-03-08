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


class DownloadRequest(EndpointResource):
    @decorators.auth.require()
    @decorators.marshal_with(DownloadURLs, code=200)
    @decorators.endpoint(
        path="/download/<marine_id>/<order_number>",
        summary="Request the download url(s) for a specific order",
        responses={"200": "Download URL(s) returned"},
    )
    def get(self, marine_id: str, order_number: str) -> Response:

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
