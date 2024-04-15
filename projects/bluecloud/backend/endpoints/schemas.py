from typing import Dict, Optional, TypedDict

from restapi.config import TESTING
from restapi.models import Schema, fields


class DownloadType(TypedDict):
    url: str
    filename: str
    order_line: str
    custom_headers: Optional[Dict[str, str]]


class DownloadHeaders(Schema):
    Authorization = fields.Str(required=False)
    Cookie = fields.Str(required=False)


class Download(Schema):
    # download url to get the data
    # With email 07/06/21, 11:19 they asked to remove the URL validator...
    # url = fields.Url(required=True)
    url = fields.Str(required=True)
    # the new filename for the datafile
    filename = fields.Str(required=True)
    # unique number for identification
    order_line = fields.Str(required=True)
    custom_headers = fields.Nested(DownloadHeaders, required=False)


class OrderInputSchema(Schema):
    # Unique Id number for debugging and communication
    request_id = fields.Str(required=True)
    # Unique ID to identify the web-site user
    marine_id = fields.Str(required=True)
    # Unique order number
    order_number = fields.Str(required=True)
    # List of downloads
    downloads = fields.List(fields.Nested(Download), required=True)
    # Used to test the endpoint without call back Maris
    # During tests is automatically defaulted to True ( === TESTING)
    debug = fields.Boolean(load_default=TESTING)
