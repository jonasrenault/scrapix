import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

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
    ] = Path("./images"),
    limit: Annotated[int, typer.Option(help="Max number of images to download.")] = 50,
    min_res: Annotated[
        tuple[int, int], typer.Option(help="Min resolution (width, height).")
    ] = (400, 300),
    max_res: Annotated[
        tuple[int, int], typer.Option(help="Max resolution (width, height).")
    ] = (2048, 2048),
):
    scraper = GoogleImageScraper(output)
    scraper.get_image_urls(query, limit, min_res, max_res)


if __name__ == "__main__":
    app()
