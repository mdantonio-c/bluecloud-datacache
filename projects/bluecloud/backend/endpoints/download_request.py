import os
from pathlib import Path
from typing import Dict, List, Union

from bluecloud.endpoints import get_seed_path, get_token
from restapi import decorators
from restapi.config import get_backend_url
from restapi.exceptions import NotFound
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log


class DownloadURL(Schema):
    url = fields.URL()
    size = fields.Int()


class DownloadURLs(Schema):
    urls = fields.Nested(DownloadURL(many=True))


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
        data: Dict[str, List[Dict[str, Union[str, int]]]] = {"urls": []}
        host = get_backend_url()

        seed_path = get_seed_path(path)

        if seed_path.exists():
            log.info("Invalidating previous download URLs")
            seed_path.unlink()

        for z in path.glob("*.zip"):

            # This is the string that will be encoded in the token
            zip_path = os.path.join(marine_id, order_number, z.name)

            filesize = path.joinpath(z.name).stat().st_size

            log.info("Request download url for {} [size={}]", zip_path, filesize)

            token = get_token(path, zip_path)

            data["urls"].append(
                {
                    "url": f"{host}/api/download/{token}",
                    "size": filesize,
                }
            )

        return self.response(data)
