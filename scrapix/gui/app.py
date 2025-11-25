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


def clear_state():
    """
    Initialize / clear session state to default values.
    """
    if "errors" not in st.session_state:
        st.session_state.errors = []
    if "urls" not in st.session_state:
        st.session_state.urls = []


clear_state()


with st.container():
    for error in st.session_state.errors:
        st.error(error)

results_placeholder = st.empty()
results_height = 400
results_container = results_placeholder.container(
    height=results_height if st.session_state.urls else "content"
)
results_container.empty()
urls_cols = results_container.columns(3)
for idx, url in enumerate(st.session_state.urls):
    urls_cols[idx % len(urls_cols)].image(url.url, caption=url.title)

parameters_container = st.container()


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
        st.session_state.urls.append(url)
        cols[count % len(cols)].image(url.url, caption=url.title)
        count += 1
        pbar.progress(count / limit, text=progress_text + f"\t{count}/{limit}")

    pbar.empty()


def on_scrape() -> None:
    st.session_state.errors = []
    st.session_state.urls = []
    results_placeholder.empty()
    results_container = results_placeholder.container(height=results_height)

    if not st.session_state.query:
        st.session_state.errors.append("Please enter a valid search query.")

    if st.session_state.errors:
        return

    output = Path(st.session_state.save_dir)
    min_res: tuple[int, int] | None = None
    max_res: tuple[int, int] | None = None
    if st.session_state.min_width > 0 and st.session_state.min_height > 0:
        min_res = (st.session_state.min_width, st.session_state.min_height)
    if st.session_state.max_width > 0 and st.session_state.max_height > 0:
        max_res = (st.session_state.max_width, st.session_state.max_height)

    asyncio.run(
        scrape_urls(
            st.session_state.query,
            output.joinpath(st.session_state.query),
            st.session_state.keywords,
            st.session_state.limit,
            st.session_state.skip,
            min_res,
            max_res,
            st.session_state.headless,
            results_container,
        )
    )

    results_placeholder.empty()


def display_scrape_parameters() -> None:
    with parameters_container.form("input_form"):
        st.text_input(
            "Google Search query",
            key="query",
            placeholder="Search for images on Google ...",
        )
        st.text_input(
            "Save directory",
            key="save_dir",
            value=settings.SCRAPIX_HOME_DIR,
            help="Directory where images and urls will be saved.",
        )
        st.multiselect(
            "Keywords",
            [],
            key="keywords",
            accept_new_options=True,
            help="Keywords to exclude in image urls or titles.",
        )

        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Limit",
                key="limit",
                min_value=1,
                value=5,
                help="Max number of images to fetch.",
            )
        with col2:
            st.number_input(
                "Skip",
                key="skip",
                min_value=0,
                help="Number of images in search results to skip.",
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.number_input(
                "Min width",
                key="min_width",
                min_value=0,
                max_value=4096,
                help="Minimum width of images in pixels.",
            )
        with col2:
            st.number_input(
                "Min height",
                key="min_height",
                min_value=0,
                max_value=4096,
                help="Minimum height of images in pixels.",
            )
        with col3:
            st.number_input(
                "Max width",
                key="max_width",
                min_value=0,
                max_value=4096,
                help="Maximum width of images in pixels.",
            )
        with col4:
            st.number_input(
                "Max height",
                key="max_height",
                min_value=0,
                max_value=4096,
                help="Maximum height of images in pixels.",
            )

        col1, col2 = st.columns(2)
        with col1:
            st.checkbox(
                "Headless",
                key="headless",
                value=True,
                help="Run scraping in headless mode, without browser GUI.",
            )
        with col2:
            st.form_submit_button(
                "Scrape !",
                icon="🚀",
                on_click=on_scrape,
            )


display_scrape_parameters()
