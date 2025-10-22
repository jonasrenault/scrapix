import json
import logging
import random
import time
from pathlib import Path
from typing import Annotated
from urllib.request import Request, urlopen
from uuid import uuid4

import typer
from fake_useragent import UserAgent
from PIL import Image
from rich.logging import RichHandler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

from scrapix.config.settings import settings

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True)]
)
LOGGER = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True)


class GoogleImageScraper:
    KEYWORDS = ["art", "model", "3D", "toy", "jouet", "jeu", "miniature", "maquette"]

    def __init__(
        self,
        save_dir: Path,
        search_term: str = "t90",
        max_images: int = 10,
        headless: bool = True,
        min_resolution: tuple[int, int] = (640, 300),
        max_resolution: tuple[int, int] = (2048, 2048),
    ):
        self.search_term = search_term
        self.max_images = max_images
        self.headless = headless
        self.min_resolution = min_resolution
        self.max_resolution = max_resolution

        options = Options()
        if headless:
            options.add_argument("--headless")

        # Set random user agent
        user_agent = UserAgent().random
        options.add_argument(f"--user-agent={user_agent}")
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=options)

        # set random window size
        self.driver.set_window_size(random.randint(1000, 2080), random.randint(800, 2080))
        google_home = "https://www.google.com"
        self.driver.get(google_home)
        LOGGER.info(
            f"Chrome web driver initialized. "
            f"Page title for {google_home}: {self.driver.title}"
        )

        self.save_dir = save_dir / search_term
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)

        # Read metadata info if present
        self.metadata_file = self.save_dir / "metadata.jsonl"
        self.saved_files = []
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                self.saved_files = [json.loads(line) for line in f.readlines()]
        self.downloaded_urls = set(map(lambda x: x["url"], self.saved_files))

    def _refuse_rgpd(self):
        """
        Refuse cookie policy. Refuse button has id W0wltc.
        """
        try:
            LOGGER.info("Clicking on Refuse cookie policy...")
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "W0wltc"))
            ).click()
        except Exception as e:
            self.driver.save_screenshot("exception.png")
            LOGGER.warning("Exception clicking on refuse cookie button")
            raise e

    def _click_recaptcha(self):
        # https://stackoverflow.com/questions/58872451/how-can-i-bypass-the-google-captcha-with-selenium-and-python
        try:
            LOGGER.info("Clicking on reCaptch")
            WebDriverWait(self.driver, 5).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (
                        By.CSS_SELECTOR,
                        "iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']",
                    )
                )
            )
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@id='recaptcha-anchor']"))
            ).click()
        except Exception as e:
            self.driver.save_screenshot("exception.png")
            LOGGER.warning("Exception clicking on reCaptcha", exc_info=True)
            raise e

    def _extract_image_url(self) -> tuple[str | None, str | None]:
        """
        Look for a valid image tag in the page.

        Returns
        -------
        tuple[str, str]
            the image's url and title
        """
        for class_name in ["n3VNCb", "iPVvYb", "r48jcc", "pT0Scc"]:
            for image in self.driver.find_elements(By.CLASS_NAME, class_name):
                url = image.get_attribute("src")
                if url and "http" in url and "encrypted" not in url:
                    return url, image.get_attribute("alt")
        return None, None

    def _filter_image(self, url: str, title: str) -> bool:
        """
        Filter image based on unwanted keywords

        Parameters
        ----------
        url : str
            the image's url
        title : str
            the image's title

        Returns
        -------
        bool
            False if image should be discarded, True otherwise
        """
        for kw in self.KEYWORDS:
            if kw.lower() in url.lower() or kw.lower() in title.lower():
                return False

        return True

    def get_image_urls(self) -> dict[str, str]:
        """
        Get image urls for a given search term

        Returns
        -------
        dict[str, str]
            a dict of url -> image title
        """

        # First, do a regular search for the term, and refuse cookie policy popup.
        LOGGER.info(f"Searching images for {self.search_term}")
        self.driver.get(f"https://www.google.com/search?q={self.search_term}")
        try:
            self._refuse_rgpd()
        except Exception:
            self._click_recaptcha()
            self._refuse_rgpd()

        # Click on images search button.
        LOGGER.info("Clicking Images search button")
        image_search = self.driver.find_element(By.LINK_TEXT, "Images")
        image_search.click()

        # Loop through all the thumbnails, stopping when we found enough images or
        # when results are exhausted.
        image_urls: dict[str, str] = {}
        visited_thumbnails: list[WebElement] = []
        new_results = True
        while len(image_urls) < self.max_images and new_results:
            # Fetch thumbnails
            LOGGER.info("Fetching thumbnails.")
            thumbnails = self.driver.find_elements(By.CSS_SELECTOR, "#islrg img.Q4LuWd")

            # Check that we have new results
            new_results = len(thumbnails) - len(visited_thumbnails) > 0
            LOGGER.info(
                f"Found {len(thumbnails)} thumbnails "
                f"({len(thumbnails) - len(visited_thumbnails)} new)."
            )

            # try to click on every new thumbnail to get the real image behind it
            for img in tqdm(thumbnails[len(visited_thumbnails) :]):
                try:
                    # Using EC.element_to_be_clickable will scroll down to the element
                    # (the element needs to be in the viewport to be clickable).
                    # This is important as scrolling down will load more results
                    # on the page.
                    WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(img)
                    ).click()
                    time.sleep(0.5)
                except Exception:
                    LOGGER.warning(f"Exception clicking thumbnail {img}", exc_info=True)
                    continue

                # After clicking on a thumbnail, get the image url and title from the
                # side panel.
                url, title = self._extract_image_url()
                if (
                    url is not None
                    and title is not None
                    and self._filter_image(url, title)
                    and url not in self.downloaded_urls
                ):
                    image_urls[url] = title
                    LOGGER.debug(f"{len(image_urls)}\t{title}\t{url}")

                if len(image_urls) >= self.max_images:
                    break

            # Keep track of thumbnails already seen
            visited_thumbnails = thumbnails
        return image_urls

    def save_images(self, image_urls: dict[str, str]) -> None:
        LOGGER.info("Saving images to disk.")

        for url, title in tqdm(image_urls.items()):
            if url in self.downloaded_urls:
                LOGGER.info(f"Not downloading {url} as it already exists.")
                continue

            try:
                with Image.open(urlopen(Request(url, headers=settings.HEADERS))) as image:
                    id = uuid4()
                    filename = f"{id}.{image.format}"
                    if image.size is None or (
                        self.min_resolution[0] <= image.size[0] <= self.max_resolution[0]
                        and self.min_resolution[1]
                        <= image.size[1]
                        <= self.max_resolution[1]
                    ):
                        try:
                            image.save(self.save_dir / filename)
                        except OSError:
                            image = image.convert("RGB")
                            image.save(self.save_dir / filename)

                        self.saved_files.append(
                            {
                                "id": str(id),
                                "url": url,
                                "title": title,
                                "size": image.size,
                            }
                        )
                    else:
                        LOGGER.debug(
                            f"Not saving image {url} because of invalid dimension "
                            f"({image.size})"
                        )
            except Exception:
                LOGGER.warning(f"Exception saving image {url}", exc_info=True)
                continue

        LOGGER.info("Writing metadata file.")
        # Write metadata
        with open(self.metadata_file, "w") as f:
            for image in self.saved_files:
                f.write(json.dumps(image) + "\n")


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
    scraper = GoogleImageScraper(
        output, query, max_images=limit, min_resolution=min_res, max_resolution=max_res
    )
    image_urls = scraper.get_image_urls()
    scraper.save_images(image_urls)


if __name__ == "__main__":
    app()
