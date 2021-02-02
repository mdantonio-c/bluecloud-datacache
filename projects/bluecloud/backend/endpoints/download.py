from restapi import decorators
from restapi.models import Schema, fields
from restapi.rest.definition import EndpointResource, Response


class DownloadURLs(Schema):
    urls = fields.List(fields.URL())


class Download(EndpointResource):

    labels = ["custom"]

    @decorators.auth.require()
    @decorators.endpoint(
        path="/download/<token>",
        summary="Download a file",
        responses={
            "200": "..."
        }
    )
    def get(self, token: str) -> Response:

        # validate the token
        # send the file content

        return self.response("")

    @decorators.auth.require()
    @decorators.marshal_with(DownloadURLs, code=400)
    @decorators.endpoint(
        path="/download/<uuid>",
        summary="Request a download url for an order",
        responses={
            "200": "Download URL(s) returned"
        }
    )
    def post(self, uuid: str) -> Response:

        # verify if order exists or return 404

        # invalidate previously created urls for this order

        # create one or more urls and get back as response

        data = {
            "urls": []
        }
        return self.response(data)
