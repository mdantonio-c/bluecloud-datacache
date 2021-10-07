import ftplib
import json
import re
import shutil
import socket
import time
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, TypedDict
from urllib.parse import urlparse

import requests
from bluecloud.endpoints.schemas import DownloadType
from celery.app.task import Task
from plumbum import local
from plumbum.commands.processes import ProcessExecutionError
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


def http_download(url: str, out_path: Path) -> Optional[Tuple[str, str]]:

    try:
        r = requests.get(
            url,
            stream=True,
            verify=False,
            headers=DOWNLOAD_HEADERS,
        )

        if r.status_code != 200:
            log.error("Invalid response from {}: {}", url, r.status_code)

            return ErrorCodes.INVALID_RESPONSE

        with open(out_path, "wb") as downloaded_file:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    downloaded_file.write(chunk)

    except requests.exceptions.ConnectionError as e:
        log.error(e)
        return ErrorCodes.UNREACHABLE_DOWNLOAD_PATH
    except requests.exceptions.MissingSchema as e:
        log.error(e)
        return ErrorCodes.UNREACHABLE_DOWNLOAD_PATH

    return None


def ftp_download(url: str, out_path: Path) -> Optional[Tuple[str, str]]:

    try:
        parsed = urlparse(url)
        ftp = ftplib.FTP(parsed.netloc)
        ftp.login()
        # ftp.login(username, password)
        with open(out_path, "wb") as downloaded_file:
            ftp.retrbinary(f"RETR {parsed.path}", downloaded_file.write)
    except socket.gaierror as e:
        log.error(e)
        return ErrorCodes.UNREACHABLE_DOWNLOAD_PATH
    except ftplib.error_perm as e:
        log.error(e)
        return ErrorCodes.UNREACHABLE_DOWNLOAD_PATH

    return None


def count_files(z: Path) -> int:
    try:
        with zipfile.ZipFile(z, "r") as myzip:
            return len(myzip.infolist())
    except zipfile.BadZipFile:  # pragma: no cover
        return 0


def make_zip_archives(
    path: Path, zip_file: Path, datadir: Path
) -> Tuple[Path, List[Path]]:

    MAX_ZIP_SIZE = Env.get_int("MAX_ZIP_SIZE")

    oversize_cache = datadir.parent.joinpath("cache_oversize")
    # Move any over-size file in the oversize cache
    for f in datadir.glob("*"):
        if f.stat().st_size > MAX_ZIP_SIZE:
            if not oversize_cache.exists():
                oversize_cache.mkdir()
            log.warning("Too large file found: {}, moving to oversize cache", f)
            f.rename(oversize_cache.joinpath(f.name))

    # Delete the split folder if already exists and create it,
    # This way the split will always start from a clean environment
    split_path = path.joinpath("zip_split")

    if split_path.exists():
        shutil.rmtree(split_path)
    split_path.mkdir()

    shutil.make_archive(base_name=str(zip_file), format="zip", root_dir=datadir)

    z = zip_file.with_suffix(".zip")

    size = z.stat().st_size

    zip_chunks: List[Path] = []
    if size > MAX_ZIP_SIZE:

        log.warning(
            "{}: zip too large, splitting {} (size {}, maxsize {})",
            path,
            z,
            size,
            MAX_ZIP_SIZE,
        )

        # Execute the split of the zip
        split_params = [
            "-n",
            MAX_ZIP_SIZE,
            "-b",
            split_path,
            z,
        ]
        try:
            zipsplit = local["/usr/bin/zipsplit"]
            zipsplit(split_params)

            log.info("{}: split completed", path)

            zip_chunks = list(split_path.glob("*.zip"))
        except ProcessExecutionError as e:

            if "Entry is larger than max split size" in e.stdout:
                reg = r"Entry too big to split, read, or write \((.*)\)"
                extra = None
                if m := re.search(reg, e.stdout):
                    extra = m.group(1)
                # ErrorCodes.ZIP_SPLIT_ENTRY_TOO_LARGE
                log.error("{}: entry is larger than max split size: {}", path, extra)
            else:
                # ErrorCodes.ZIP_SPLIT_ERROR
                log.error("{}: {}", path, e.stdout)

            return z, []

    oversize_cache_list = list(oversize_cache.glob("*"))

    # One or more over-size file have to added to the output
    # They are not included in the normal zip & zipsplit workflow
    # Because zipsplit would fail when the zip file contains a file larger then MAX_SIZE
    if oversize_cache_list:

        index = len(zip_chunks)

        if index == 0:
            # chunks are ZERO => zipsplit not executed and output.zip
            # is to be considered as chunk 1
            # BUT only if it is not empty
            if count_files(z) > 0:
                chunk_path = split_path.joinpath("output1.zip")
                z.rename(chunk_path)
                zip_chunks.append(chunk_path)
                index = 1

        for f in oversize_cache_list:
            # Can't safely go outside the loop because if the order does not contain
            # any over size file then the oversize_cache folder does not exist
            tmp_dir = oversize_cache.joinpath("tmp")
            tmp_dir.mkdir(exist_ok=True)
            index += 1
            chunk_path = split_path.joinpath(f"output{index}")
            # make_archive can't create an archive from file, but only from a folder...
            tmp_file = tmp_dir.joinpath(f.name)
            f.rename(tmp_file)
            shutil.make_archive(
                base_name=str(chunk_path), format="zip", root_dir=tmp_dir
            )
            # move back the file on the oversize_cache cache
            tmp_file.rename(f)

            shutil.rmtree(tmp_dir)
            zip_chunks.append(chunk_path.with_suffix(".zip"))

    if zip_chunks:

        log.info("{}: split completed, moving files", path)
        # remove the whole zip to save space
        # and move all split zips on the main folder
        # Note that the whole zip may not exist in the case of small zip (so not split)
        # and a too-large file. In this case the whole zip is moved as chunk1
        if z.exists():
            z.unlink()

        for f in zip_chunks:

            p = f.absolute()
            parent_dir = p.parents[1]
            p.rename(parent_dir.joinpath(p.name))

        log.warning("{}: split completed", path)

    # Just a final check to verify how many chunks we have
    # In case of a single too large file the current situation would be:
    # output.zip empty because no normal files have been merged
    # cache empty
    # zip path empty
    # oversize cache contains 1 file archived in output1.zip
    # In this very specific case output1.zip has to be renamed into output.zip
    output1 = path.joinpath("output1.zip")
    output2 = path.joinpath("output2.zip")
    # not that len(zip_chunks) == 1 is redundant, but added for a safer check
    if output1.exists() and not output2.exists() and len(zip_chunks) == 1:
        output1.rename(z)
        return z, []

    return z, zip_chunks


@CeleryExt.task()
def make_order(
    self: Task,
    request_id: str,
    marine_id: str,
    order_number: str,
    downloads: List[DownloadType],
    debug: bool,
) -> ResponseType:

    path = Uploader.absolute_upload_file(order_number, subfolder=Path(marine_id))

    log.warning("{}: starting task with {} download(s)", path, len(downloads))

    # it is expected to be created by the endpoint
    if not path.exists():
        raise NotFound(str(path))

    # Do not include the .zip extension
    zip_file = path.joinpath("output")
    cache = path.joinpath("cache")
    logs = path.joinpath("logs")
    lock = path.joinpath("lock")

    cache.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)

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

            local_path = cache.joinpath(filename)

            if download_url.startswith("ftp://"):
                error = ftp_download(download_url, local_path)
            else:
                error = http_download(download_url, local_path)

            if error:
                response["errors"].append(
                    {
                        "url": download_url,
                        "order_line": order_line,
                        "error_number": error[0],
                    }
                )
                continue

            downloaded += 1

        except Exception as e:  # pragma: no cover
            log.error("{}: {}", path, e)
            response["errors"].append(
                {
                    "url": download_url,
                    "order_line": order_line,
                    "error_number": ErrorCodes.UNEXPECTED_ERROR[0],
                }
            )
            continue

    log.warning("{}: downloaded {} file(s)", path, downloaded)

    if downloaded > 0:

        LOCK_SLEEP_TIME = Env.get_int("LOCK_SLEEP_TIME")
        while lock.exists():  # pragma: no cover
            log.warning("{}: found a lock ({}), waiting", path, lock)
            time.sleep(LOCK_SLEEP_TIME)
        lock.touch(exist_ok=False)

        try:

            whole_zip, zip_chunks = make_zip_archives(path, zip_file, cache)

            lock.unlink()
        # should never happens, but it is added to prevent problems with lock release
        except Exception as e:  # pragma: no cover
            log.error("{}: {}", path, e)
            lock.unlink()
            raise e

    log.warning("{}: task completed", path)

    # uhm... last execution override previous response...
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
                "{}: failed to call external API (status: {}, uri: {})",
                path,
                r.status_code,
                FULL_URL,
            )
        else:
            log.warning(
                "{}: called POST on external API (status: {}, uri: {})",
                path,
                r.status_code,
                FULL_URL,
            )

    return response
