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

        zippath = UPLOAD_PATH.joinpath(path)

        if not zippath.exists():
            raise BadRequest("Invalid token")

        log.info("Request download for path: {}", zippath)

        return Downloader.send_file_streamed(zippath)
