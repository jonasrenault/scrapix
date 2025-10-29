import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

from scrapix.config.settings import settings
from scrapix.scraper import GoogleImageScraper
from scrapix.urls import download_urls, read_urls

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)
app = typer.Typer(no_args_is_help=True)


@app.command()
def download(
    save_dir: Annotated[
        Path, typer.Argument(dir_okay=True, file_okay=False, help="Save directory.")
    ],
    urls_file: Annotated[
        Path,
        typer.Option(
            "--urls", "-u", dir_okay=False, file_okay=True, help="Urls file name."
        ),
    ] = Path("urls.json"),
    force: Annotated[
        bool,
        typer.Option(help="Force redownload of images already present on disk."),
    ] = False,
):
    """
    Download images to disk from a list of image urls.

    Args:
        save_dir (Path): Save directory where downloaded images will be saved.
        urls_file (Path, optional): Urls file name. Defaults to Path("urls.json").
        force (bool, optional): Force redownload of images already present on disk.
            Defaults to False.

    Raises:
        ValueError: if urls_file does not exist.
    """
    if not urls_file.exists() or not urls_file.is_file():
        urls_file = save_dir / urls_file

    if not urls_file.exists() or not urls_file.is_file():
        raise ValueError(f"Unable to locate urls file {urls_file}.")

    urls = read_urls(urls_file)
    download_urls(urls, save_dir=save_dir, force=force)


@app.command()
def scrape(
    query: Annotated[str, typer.Argument(help="Search query.")],
    output: Annotated[
        Path,
        typer.Option(
            "--dir",
            "-d",
            help="Save directory.",
            dir_okay=True,
            file_okay=False,
        ),
    ] = settings.SCRAPIX_HOME_DIR,
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Max number of images to download.")
    ] = 10,
    skip: Annotated[
        int, typer.Option("--skip", "-s", help="Number of results to skip.")
    ] = 0,
    keywords: Annotated[
        list[str], typer.Option("--keywords", "-k", help="Keywords to exclude.")
    ] = [],
    min_res: Annotated[
        tuple[int, int] | None,
        typer.Option("--min", help="Minimum resolution of images."),
    ] = None,
    max_res: Annotated[
        tuple[int, int] | None,
        typer.Option("--max", help="Maximum resolution of images."),
    ] = None,
    download: Annotated[
        bool, typer.Option(help="Save images on disk after scraping the urls.")
    ] = True,
    force: Annotated[
        bool,
        typer.Option(help="Force redownload of images already present on disk."),
    ] = False,
):
    save_dir = output.joinpath(query)
    scraper = GoogleImageScraper(save_dir)
    urls = scraper.get_image_urls(
        query, limit=limit, skip=skip, keywords=keywords, min_res=min_res, max_res=max_res
    )

    if download:
        download_urls(urls, save_dir=save_dir, force=force)


if __name__ == "__main__":
    app()
