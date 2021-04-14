import os
from pathlib import Path
from typing import Dict, List

from bluecloud.endpoints import get_seed_path, get_token
from restapi import decorators
from restapi.config import get_backend_url
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
        responses={
            200: "Download URL(s) returned",
            404: "The requested order cannot be found",
        },
    )
    def get(self, marine_id: str, order_number: str) -> Response:

        path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

        if not path.exists():
            raise NotFound(
                f"Order {order_number} does not exist for marine id {marine_id}"
            )

        # Create one or more urls and get back as response
        # Previously created urls for this order will be invalidated
        data: Dict[str, List[str]] = {"urls": []}
        host = get_backend_url()

        abs_zippath = Uploader.absolute_upload_file(
            order_number, subfolder=Path(marine_id)
        )

        seed_path = get_seed_path(abs_zippath)

        if seed_path.exists():
            log.info("Invalidating previous download URLs")
            seed_path.unlink()

        for z in path.glob("*.zip"):

            zip_path = os.path.join(marine_id, order_number, z.name)

            filesize = zip_path.stat().st_size

            log.info("Request download url for {} [size={}]", zip_path, filesize)

            token = get_token(abs_zippath, zip_path)

            data["urls"].append(f"{host}/api/download/{token}")

        return self.response(data)
