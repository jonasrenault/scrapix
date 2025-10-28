import dataclasses
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Self


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
