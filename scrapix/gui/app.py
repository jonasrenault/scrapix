import asyncio
from pathlib import Path

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from scrapix.config.settings import settings
from scrapix.scraper import GoogleImageScraper

# Set page title
st.set_page_config(
    page_title="Scrapix - Smart, fast, and simple image scraper for Google Images Search",
    page_icon=":framed_picture:",
    # layout="wide",
)

st.title(
    ":framed_picture: Scrapix - Smart, fast, and simple image scraper for "
    "Google Images Search"
)
st.markdown(
    """
    Scrapix is an automated image scraper designed to collect pictures from Google Images
    Search. Enter your search query below and start scraping.
    """,
)


async def scrape_urls(
    query: str,
    save_dir: Path,
    keywords: list[str],
    limit: int,
    skip: int,
    min_res: tuple[int, int] | None,
    max_res: tuple[int, int] | None,
    headless: bool,
    results_container: DeltaGenerator,
):
    scraper = await GoogleImageScraper.create(save_dir, headless=headless)
    progress_text = "Scraping images..."
    pbar = results_container.progress(0, text=progress_text)
    count = 0
    cols = results_container.columns(3)
    async for url in scraper.get_image_urls(
        query, limit=limit, skip=skip, keywords=keywords, min_res=min_res, max_res=max_res
    ):
        cols[count % len(cols)].image(url.url, caption=url.title)
        count += 1
        pbar.progress(count / limit)

    pbar.empty()


def on_scrape(
    query: str,
    save_dir: str,
    keywords: list[str],
    limit: int,
    skip: int,
    min_width: int,
    max_width: int,
    min_height: int,
    max_height: int,
    headless: bool,
    errors_placeholder: DeltaGenerator,
    results_placeholder: DeltaGenerator,
):
    error = False
    error_container = errors_placeholder.container()
    results_container = results_placeholder.container()

    if not query:
        error_container.error("Please enter a valid search query.")
        error = True

    output = Path(save_dir)
    if not output.is_dir():
        error_container.error(f"{output} is not a valid directory.")
        error = True

    if error:
        return

    min_res: tuple[int, int] | None = None
    max_res: tuple[int, int] | None = None
    if min_width > 0 and min_height > 0:
        min_res = (min_width, min_height)
    if max_width > 0 and max_height > 0:
        max_res = (max_width, max_height)

    asyncio.run(
        scrape_urls(
            query,
            output.joinpath(query),
            keywords,
            limit,
            skip,
            min_res,
            max_res,
            headless,
            results_container,
        )
    )


def display_scrape_parameters(
    parameters_container: DeltaGenerator,
    errors_placeholder: DeltaGenerator,
    results_placeholder: DeltaGenerator,
):
    query = parameters_container.text_input(
        "Google Search query", key="query", placeholder="Search for images on Google ..."
    )
    save_dir = parameters_container.text_input(
        "Save directory",
        value=settings.SCRAPIX_HOME_DIR,
        help="Directory where images and urls will be saved.",
    )
    keywords = parameters_container.multiselect(
        "Keywords",
        [],
        accept_new_options=True,
        help="Keywords to exclude in image urls or titles.",
    )

    col1, col2 = parameters_container.columns(2)
    with col1:
        limit = st.number_input(
            "Limit", min_value=1, value=10, help="Max number of images to fetch."
        )
    with col2:
        skip = st.number_input(
            "Skip", min_value=0, help="Number of images in search results to skip."
        )

    col1, col2, col3, col4 = parameters_container.columns(4)
    with col1:
        min_width = st.number_input(
            "Min width",
            min_value=0,
            max_value=4096,
            help="Minimum width of images in pixels.",
        )
    with col2:
        min_height = st.number_input(
            "Min height",
            min_value=0,
            max_value=4096,
            help="Minimum height of images in pixels.",
        )
    with col3:
        max_width = st.number_input(
            "Max width",
            min_value=0,
            max_value=4096,
            help="Maximum width of images in pixels.",
        )
    with col4:
        max_height = st.number_input(
            "Max height",
            min_value=0,
            max_value=4096,
            help="Maximum height of images in pixels.",
        )

    col1, col2 = parameters_container.columns(2)
    with col1:
        headless = st.checkbox(
            "Headless",
            value=True,
            help="Run scraping in headless mode, without browser GUI.",
        )
    with col2:
        st.button(
            "Scrape !",
            icon="🚀",
            on_click=on_scrape,
            args=(
                query,
                save_dir,
                keywords,
                limit,
                skip,
                min_width,
                min_height,
                max_width,
                max_height,
                headless,
                errors_placeholder,
                results_placeholder,
            ),
        )


errors_placeholder = st.empty()
parameters_container = st.expander("Scrape parameters", expanded=True)
results_placeholder = st.empty()
display_scrape_parameters(parameters_container, errors_placeholder, results_placeholder)
