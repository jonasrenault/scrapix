import dataclasses
import inspect
import json
import logging
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Self
from urllib.parse import unquote, urlparse

import requests
from fake_useragent import UserAgent
from PIL import Image
from tqdm import tqdm

LOGGER = logging.getLogger(__name__)


def fake_headers() -> dict[str, str]:
    """
    Generate fake http headers.

    Returns:
        dict[str, str]: fake headers.
    """
    user_agent = UserAgent(platforms=["desktop"], min_version=120.0).random
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }


@dataclass(frozen=True)
class ImageUrl:
    title: str | None
    url: str

    @property
    def filename(self) -> str:
        """
        Get filename from image url.

        Returns:
            str: the image's filename.
        """
        parsed_url = urlparse(self.url)
        path = parsed_url.path
        filename = unquote(Path(path).name)
        return filename

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Create ImageUrl instance from dict of field -> value.

        Args:
            data (dict[str, Any]): dict of field -> value.

        Returns:
            Self: An ImageUrl instance with values instantiated from dict.
        """
        instance = cls(
            **{
                key: value
                for key, value in data.items()
                if key in inspect.signature(cls).parameters
            }
        )
        return instance

    def check_dimensions(
        self,
        min_resolution: tuple[int, int] | None,
        max_resolution: tuple[int, int] | None,
    ) -> bool:
        """
        Check whether image size is between min_resolution and max_resolution.

        Args:
            min_resolution (tuple[int, int] | None): minimum resolution.
            max_resolution (tuple[int, int] | None): maximum resolution.

        Returns:
            bool: True if image dimensions are between min_resolution and max_resolution.
        """
        response = requests.get(self.url, stream=True, headers=fake_headers())
        response.raise_for_status()
        with Image.open(response.raw) as image:  # type: ignore
            if image.size is None:
                return True

            if min_resolution is not None and (
                min_resolution[0] > image.size[0] or min_resolution[1] > image.size[1]
            ):
                return False

            if max_resolution is not None and (
                max_resolution[0] < image.size[0] or max_resolution[1] < image.size[1]
            ):
                return False

            return True

    def download(self, save_dir: Path, force: bool = False):
        """
        Download image from url into save_dir. Image filename is taken
        from url. Image is not downloaded if filename already exists, unless
        force is True.

        Args:
            save_dir (Path): output directory where image is saved.
            force (bool, optional): force download if image filename already exists.
                Defaults to False.
        """
        file = save_dir / self.filename
        if file.exists() and not force:
            return

        response = requests.get(self.url, stream=True, headers=fake_headers())
        response.raise_for_status()
        with open(file, "wb") as f:
            shutil.copyfileobj(response.raw, f)


def read_urls(uri: BinaryIO | Path) -> set[ImageUrl]:
    """
    Read a list of ImageUrl as JSON data.

    Args:
        uri (BinaryIO | Path): input JSON file.

    Returns:
        set[ImageUrl]: list of ImageUrl.
    """
    if isinstance(uri, BinaryIO):
        json_data = json.load(uri)
    else:
        with open(uri, "r") as f:
            json_data = json.load(f)
    urls = set([ImageUrl.from_dict(url) for url in json_data])
    return urls


def write_urls(urls: set[ImageUrl], file: Path) -> None:
    """
    Write ImageUrls as JSON data.

    Args:
        urls (set[ImageUrl]): the set of ImageUrls.
        file (Path): the output file.
    """
    json_data = [dataclasses.asdict(url) for url in urls]
    with open(file, "w") as f:
        json.dump(json_data, f, indent=2)


def download_urls(urls: Iterable[ImageUrl], save_dir: Path, force: bool = False):
    LOGGER.info(f"Downloading images to {save_dir}.")
    for url in tqdm(urls):
        url.download(save_dir=save_dir, force=force)
