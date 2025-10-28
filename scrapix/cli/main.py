import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

from scrapix.config.settings import settings
from scrapix.scraper import GoogleImageScraper

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)

app = typer.Typer(no_args_is_help=True)


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
    limit: Annotated[int, typer.Option(help="Max number of images to download.")] = 10,
    skip: Annotated[int, typer.Option(help="Number of results to skip.")] = 0,
):
    scraper = GoogleImageScraper(output.joinpath(query))
    scraper.get_image_urls(query, limit=limit, skip=skip)


if __name__ == "__main__":
    app()
