import hashlib
import os
import tempfile
import urllib.request

from src import log

LOGGER = log.new_logger(__name__)

_CHUNK_SIZE = 1 << 20


def ensure_asset(lurker_home: str, relative_path: str, url: str, sha256: str | None = None) -> str:
    """Return ``<lurker_home>/<relative_path>``, downloading it once if it is missing."""
    target = os.path.join(lurker_home, relative_path)
    if os.path.isfile(target):
        return target

    target_dir = os.path.dirname(target)
    os.makedirs(target_dir, exist_ok=True)
    LOGGER.info(f"Downloading missing asset {url} to {target}")

    file_descriptor, temp_path = tempfile.mkstemp(dir=target_dir, prefix=".download-")
    try:
        with os.fdopen(file_descriptor, "wb") as temp_file:
            with urllib.request.urlopen(url, timeout=60) as response:
                while chunk := response.read(_CHUNK_SIZE):
                    temp_file.write(chunk)

        if sha256 is not None:
            digest = hashlib.sha256()
            with open(temp_path, "rb") as downloaded:
                for chunk in iter(lambda: downloaded.read(_CHUNK_SIZE), b""):
                    digest.update(chunk)
            if digest.hexdigest() != sha256:
                raise ValueError(
                    f"Checksum mismatch for {url}: expected {sha256}, got {digest.hexdigest()}"
                )

        os.replace(temp_path, target)
    except BaseException:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise
    return target
