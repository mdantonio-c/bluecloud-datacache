from restapi import decorators
from restapi.rest.definition import EndpointResource, Response


class Download(EndpointResource):

    labels = ["download"]

    @decorators.endpoint(
        path="/download/<token>", summary="Download a file", responses={"200": "..."}
    )
    def get(self, token: str) -> Response:

        # validate the token
        # send the file content

        return self.response("")
