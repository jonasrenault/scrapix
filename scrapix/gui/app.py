import streamlit as st

from scrapix.config.settings import settings

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
    Search based on user-defined queries. It streamlines the process of fetching,
    filtering, and storing image results for use in datasets, research,
    or creative projects.
    """,
)

with st.container():
    query = st.text_input(
        "Google Search query",
        key="query",
    )
    save_dir = st.text_input(
        "Save directory",
        value=settings.SCRAPIX_HOME_DIR,
        help="Directory where images and urls will be saved.",
    )
    keywords = st.multiselect(
        "Keywords",
        [],
        accept_new_options=True,
        help="Keywords to exclude in image urls or titles.",
    )

    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input(
            "limit", min_value=0, value=10, help="Max number of images to fetch."
        )
    with col2:
        skip = st.number_input(
            "skip", min_value=0, help="Number of images in search results to skip."
        )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        min_width = st.number_input("min width", min_value=0, max_value=4096)
    with col2:
        min_height = st.number_input("min height", min_value=0, max_value=4096)
    with col3:
        max_width = st.number_input("max width", min_value=0, max_value=4096)
    with col4:
        max_height = st.number_input("max height", min_value=0, max_value=4096)

    col1, col2 = st.columns(2)
    with col1:
        headless = st.checkbox(
            "Headless", help="Run browser in headless mode, without GUI."
        )
    with col2:
        st.button("Scrape !", icon="🚀")
