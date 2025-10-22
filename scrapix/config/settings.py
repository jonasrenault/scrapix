from pathlib import Path
from typing import ClassVar

from fake_useragent import UserAgent
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    SCRAPIX_HOME_DIR: Path = Path.home() / ".cache" / "scrapix"

    HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": UserAgent().random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",  # noqa: E501
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }


settings = Settings()
