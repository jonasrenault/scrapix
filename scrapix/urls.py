import dataclasses
import inspect
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Self
from urllib.parse import unquote, urlparse

import requests
from fake_useragent import UserAgent
from PIL import Image


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
        self, min_resolution: tuple[int, int], max_resolution: tuple[int, int]
    ) -> bool:
        """
        Check whether image size is between min_resolution and max_resolution.

        Args:
            min_resolution (tuple[int, int]): minimum resolution.
            max_resolution (tuple[int, int]): maximum resolution.

        Returns:
            bool: True if image dimensions are between min_resolution and max_resolution.
        """
        response = requests.get(self.url, stream=True, headers=fake_headers())
        response.raise_for_status()
        with Image.open(response.raw) as image:  # type: ignore
            return image.size is None or (
                min_resolution[0] <= image.size[0] <= max_resolution[0]
                and min_resolution[1] <= image.size[1] <= max_resolution[1]
            )

    def download(self, save_dir: Path):
        """
        Download image from url into save_dir. Image filename is taken
        from url.

        Args:
            save_dir (Path): output directory where image is saved.
        """
        response = requests.get(self.url, stream=True, headers=fake_headers())
        response.raise_for_status()
        file = save_dir / get_filename(self.url)
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


def get_filename(url: str) -> str:
    """
    Get filename from image url.

    Args:
        url (str): the image's url

    Returns:
        str: the image's filename.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = unquote(Path(path).name)
    return filename
