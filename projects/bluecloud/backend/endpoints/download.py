import re

from bluecloud.endpoints import read_token
from restapi import decorators
from restapi.config import UPLOAD_PATH
from restapi.exceptions import BadRequest
from restapi.rest.definition import EndpointResource, Response
from restapi.services.download import Downloader
from restapi.utilities.logs import log


class Download(EndpointResource):

    labels = ["download"]

    @decorators.endpoint(
        path="/download/<token>",
        summary="Download a file",
        responses={200: "Send the requested file as a stream of data"},
    )
    def get(self, token: str) -> Response:

        try:
            path = read_token(token)
        except BaseException as e:
            log.error(e)
            raise BadRequest("Invalid token")

        # zippath is /uploads/MARINE-ID/ORDER-NUMER/FILE.zip
        zippath = UPLOAD_PATH.joinpath(path)

        log.critical(zippath.name)
        # .parent /uploads/MARINE-ID/ORDER-NUMER
        # .name ORDER-NUMER
        order_num = zippath.parent.name
        # single zip
        if zippath.name == "output.zip":
            filename = f"Blue-Cloud_order_{order_num}.zip"
        # split zip
        else:
            m = re.search(r"output([0-9]+).zip", zippath.name)
            if m:
                zip_number = m.group(1)
            else:  # pragma: no cover
                log.error("Can't extract zip number from {}", zippath.name)
                zip_number = "0"
            filename = f"Blue-Cloud_order_{order_num}_{zip_number}.zip"

        if not zippath.exists():
            raise BadRequest("Invalid token")

        log.info("Request download for path: {}", zippath)

        return Downloader.send_file_streamed(zippath, out_filename=filename)
