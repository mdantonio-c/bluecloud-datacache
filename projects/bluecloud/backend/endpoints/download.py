import re

from bluecloud.endpoints import read_token
from restapi import decorators
from restapi.config import UPLOAD_PATH
from restapi.exceptions import NotFound, Unauthorized
from restapi.rest.definition import EndpointResource, Response
from restapi.services.download import Downloader
from restapi.utilities.logs import log


class Download(EndpointResource):

    labels = ["download"]

    @decorators.endpoint(
        path="/download/<token>",
        summary="Download a file",
        responses={
            200: "Send the requested file as a stream of data",
            401: "Provided token is invalid",
        },
    )
    def get(self, token: str) -> Response:

        try:
            path = read_token(token)
        except Exception as e:
            log.error(e)
            raise Unauthorized("Provided token is invalid")

        # == /uploads/MARINE-ID/ORDER-NUMER/FILE.zip
        zippath = UPLOAD_PATH.joinpath(path)
        zip_filename = zippath.name
        # == /uploads/MARINE-ID/ORDER-NUMER
        subfolder = zippath.parent
        order_num = subfolder.name

        # single zip
        if zip_filename == "output.zip":
            filename = f"Blue-Cloud_order_{order_num}.zip"
        # split zip
        else:
            m = re.search(r"output([0-9]+).zip", zip_filename)
            if m:
                zip_number = m.group(1)
            else:  # pragma: no cover
                log.error("Can't extract zip number from {}", zip_filename)
                zip_number = "0"
            filename = f"Blue-Cloud_order_{order_num}_{zip_number}.zip"

        log.info("Request download for path: {}", zippath)

        return Downloader.send_file_streamed(
            zip_filename, subfolder=subfolder, out_filename=filename
        )
