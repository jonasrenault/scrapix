from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # SCRAPIX_HOME_DIR: Path = Path.home() / ".cache" / "scrapix"
    SCRAPIX_HOME_DIR: Path = Path.cwd() / ".cache" / "scrapix"

    # Images link text at top of page after a search to switch to image results
    IMAGES_LINK_TEXT: str = "Images"
    # CSS selector for thumbnail divs on GoogleImage results page
    THUMBNAIL_DIV_SELECTOR: str = "div.F0uyec"
    # CSS classes of source images after having clicked on a thumbnail in results page
    IMAGE_CLASSES: list[str] = ["n3VNCb", "iPVvYb", "r48jcc", "pT0Scc"]


settings = Settings()
