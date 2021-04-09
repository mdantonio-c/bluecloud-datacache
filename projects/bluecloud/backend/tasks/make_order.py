import json
import shutil
from pathlib import Path
from typing import List, TypedDict

import requests
from bluecloud.endpoints.schemas import DownloadType
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from restapi.connectors.celery import CeleryExt
from restapi.env import Env
from restapi.exceptions import NotFound
from restapi.services.uploader import Uploader
from restapi.utilities.logs import log

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DownloadError(TypedDict):
    url: str
    order_line: str
    error_number: str


class ResponseType(TypedDict):
    request_id: str
    order_number: str
    errors: List[DownloadError]


DOWNLOAD_HEADERS = {
    "User-Agent": "BlueCloud DataCache HTTP-APIs",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
}


class ErrorCodes:
    UNREACHABLE_DOWNLOAD_PATH = ("001", "Download path is unreachable")
    INVALID_RESPONSE = ("002", "Invalid response, received status different than 200")
    UNEXPECTED_ERROR = ("999", "An unexpected error occurred")


@CeleryExt.task()
def make_order(
    self: CeleryExt.TaskType,
    request_id: str,
    marine_id: str,
    order_number: str,
    downloads: List[DownloadType],
    debug: bool,
) -> str:

    path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

    # it is expected to be created by the endpoint
    if not path.exists():
        raise NotFound(str(path))

    # Do not include the .zip extension
    zip_file = path.joinpath("output")
    cache = path.joinpath("cache")
    logs = path.joinpath("logs")

    cache.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)

    # log.info("Task ID: {}", self.request.id)
    # log.info("Request ID = {}", request_id)
    # log.info("Marine ID = {}", marine_id)
    # log.info("Order number = {}", order_number)
    # log.info("Download list = {}", downloads[0:10])

    response: ResponseType = {
        "request_id": request_id,
        "order_number": order_number,
        "errors": [],
    }

    downloaded: int = 0
    for d in downloads:
        download_url = d["url"]
        filename = d["filename"]
        order_line = d["order_line"]

        log.debug("{} -> {}", download_url, filename)

        try:

            r = requests.get(
                download_url,
                stream=True,
                verify=False,
                headers=DOWNLOAD_HEADERS,
            )

            if r.status_code != 200:
                log.error("Invalid response from {}: {}", download_url, r.status_code)
                response["errors"].append(
                    {
                        "url": download_url,
                        "order_line": order_line,
                        "error_number": ErrorCodes.INVALID_RESPONSE[0],
                    }
                )

                continue

            local_path = cache.joinpath(filename)

            with open(local_path, "wb") as downloaded_file:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        downloaded_file.write(chunk)

            downloaded += 1
        except requests.exceptions.ConnectionError as e:
            log.error(e)
            response["errors"].append(
                {
                    "url": download_url,
                    "order_line": order_line,
                    "error_number": ErrorCodes.UNREACHABLE_DOWNLOAD_PATH[0],
                }
            )
            continue
        except requests.exceptions.MissingSchema as e:
            log.error(e)
            response["errors"].append(
                {
                    "url": download_url,
                    "order_line": order_line,
                    "error_number": ErrorCodes.UNREACHABLE_DOWNLOAD_PATH[0],
                }
            )
            continue
        except BaseException as e:
            log.error(e)
            response["errors"].append(
                {
                    "url": download_url,
                    "order_line": order_line,
                    "error_number": ErrorCodes.UNEXPECTED_ERROR[0],
                }
            )
            continue

    log.info("Downloaded {} files", downloaded)

    if downloaded > 0:

        # Argument "base_name" to "make_archive" has incompatible type "Path";
        # expected "str"
        shutil.make_archive(base_name=str(zip_file), format="zip", root_dir=cache)

        MAX_ZIP_SIZE = Env.get("MAX_ZIP_SIZE")

        # f = f"{zip_file}.zip"
        log.critical("Zip split not implemented yet, max zip size = {}", MAX_ZIP_SIZE)

        # This is the implementation from SDC:

        # if os.path.getsize(str(zip_local_file)) > MAX_ZIP_SIZE:
        #     log.warning("Zip too large, splitting {}", zip_local_file)

        #     # Create a sub folder for split files. If already exists,
        #     # remove it before to start from a clean environment
        #     split_path = path.join(local_dir, "unrestricted_zip_split")
        #     # split_path is an object
        #     rmtree(str(split_path), ignore_errors=True)
        #     # path create requires a path object
        #     path.create(split_path, directory=True, force=True)
        #     # path object is no longer required, cast to string
        #     split_path = str(split_path)

        #     # Execute the split of the whole zip
        #     bash = BashCommands()
        #     split_params = [
        #         "-n",
        #         MAX_ZIP_SIZE,
        #         "-b",
        #         split_path,
        #         zip_local_file,
        #     ]
        #     try:
        #         out = bash.execute_command("/usr/bin/zipsplit", split_params)
        #     except ProcessExecutionError as e:

        #         if "Entry is larger than max split size" in e.stdout:
        #             reg = r"Entry too big to split, read, or write \((.*)\)"
        #             extra = None
        #             m = re.search(reg, e.stdout)
        #             if m:
        #                 extra = m.group(1)
        #             return notify_error(
        #                 ErrorCodes.ZIP_SPLIT_ENTRY_TOO_LARGE,
        #                 myjson,
        #                 backdoor,
        #                 self,
        #                 extra=extra,
        #             )
        #         else:
        #             log.error(e.stdout)

        #         return notify_error(
        #             ErrorCodes.ZIP_SPLIT_ERROR,
        #             myjson,
        #             backdoor,
        #             self,
        #             extra=str(zip_local_file),
        #         )

        #     regexp = "^.*[^0-9]([0-9]+).zip$"
        #     zip_files = os.listdir(split_path)
        #     base_filename, _ = os.path.splitext(zip_file_name)
        #     for subzip_file in zip_files:
        #         m = re.search(regexp, subzip_file)
        #         if not m:
        #             log.error(
        #                 "Cannot extract index from zip name: {}", subzip_file,
        #             )
        #             return notify_error(
        #                 ErrorCodes.INVALID_ZIP_SPLIT_OUTPUT,
        #                 myjson,
        #                 backdoor,
        #                 self,
        #                 extra=str(zip_local_file),
        #             )
        #         index = m.group(1).lstrip("0")
        #         subzip_path = path.join(split_path, subzip_file)

        #         subzip_ifile = path.append_compress_extension(
        #             f"{base_filename}{index}"
        #         )
        #         subzip_ipath = path.join(order_path, subzip_ifile)

    log.info("Task executed on {}", path)

    # uhm... last execution override previous response... is this
    log_path = logs.joinpath("response.json")
    with open(log_path, "w+") as log_file:
        log_file.write(json.dumps(response))

    EXT_URL = Env.get("MARIS_EXTERNAL_API_SERVER")
    ACTION = "download-datafiles-ready"
    FULL_URL = f"{EXT_URL}/{ACTION}"

    if debug:
        log.info("Debug mode is enabled, response not sent to {}", FULL_URL)
    else:  # pragma: no cover
        r = requests.post(FULL_URL, json=response)

        if r.status_code != 200:
            log.error(
                "Failed to call external API (status: {}, uri: {})",
                r.status_code,
                FULL_URL,
            )
        else:
            log.info(
                "Called POST on external API (status: {}, uri: {})",
                r.status_code,
                FULL_URL,
            )

    return "Task executed!"
