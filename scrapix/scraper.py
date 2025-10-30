import logging
import random
import time
from pathlib import Path

from fake_useragent import UserAgent
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scrapix.config.settings import settings
from scrapix.urls import ImageUrl, read_urls, write_urls

LOGGER = logging.getLogger(__name__)


class GoogleImageScraper:

    def __init__(
        self,
        save_dir: Path,
        headless: bool = False,
        urls_file: str = "urls.json",
        force: bool = False,
    ):
        """
        Init a GoogleImageScraper to retrieve image urls from a google search and
        save them to disk. Image urls will be saved as json in the file `urls_file`
        in the `save_dir` directory. If ImageUrls are already present in `urls_file`,
        they will be loaded and only new ImageUrls will be added to the list, unless
        force is True.

        Args:
            save_dir (Path): the directory where urls will be saved.
            headless (bool, optional): use headless web driver. Defaults to False.
            urls_file (str, optional): urls file name. Defaults to "urls.json".
            force (bool, optional): ignore urls already present in urls_file.
                Defaults to False.
        """
        self.headless = headless
        self.urls_file = urls_file
        self.save_dir = save_dir
        self.force = force
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Saving results to [bold blue]{self.save_dir}[/].")
        self._load_urls()

        self._setup_webdriver()

    def _load_urls(self) -> None:
        urls_file = self.save_dir / self.urls_file
        if urls_file.exists() and urls_file.is_file() and not self.force:
            self.urls = read_urls(self.save_dir / self.urls_file)
        else:
            self.urls = set()

    def _save_urls(self, urls: set[ImageUrl]) -> None:
        urls_file = self.save_dir / self.urls_file
        LOGGER.info(f"Saving {len(urls)} urls to {urls_file}.")
        write_urls(urls, urls_file)

    def _setup_webdriver(self):
        """
        Setup the selenium webdriver: add a random UserAgent and options to avoid
        bot detection.
        """
        self.options = Options()
        if self.headless:
            self.options.add_argument("--headless=new")

        # Set random user agent
        self.user_agent = UserAgent(platforms=["desktop"], min_version=120.0).random
        self.options.add_argument(f"--user-agent={self.user_agent}")

        # Set options to hide selenium webdriver
        self.options.add_argument("start-maximized")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=self.options)

        # set random viewport
        self.viewport = (random.randint(1000, 1100), random.randint(1101, 1250))
        self.driver.set_window_size(*self.viewport)

        LOGGER.info(f"Chrome web driver initialized. \n{self}")

    def __str__(self) -> str:
        repr_str = (
            f"{self.__class__.__name__}: Headless={self.headless}, "
            f"Viewport={self.viewport}, UserAgent={self.user_agent}, "
            f"WebDriver={self.driver.execute_script("return navigator.webdriver;")}.\n"
            f"Options: {self.options.to_capabilities()}"
        )
        return repr_str

    def _log_page(self, show: bool = False):
        """
        Log the current page in the webdriver by saving a screenshot and the full dom tree
        to disk.

        Args:
            show (bool, optional): show the screenshot. Defaults to False.
        """
        screen = self.save_dir / "screenshot.png"
        self.driver.save_screenshot(screen)
        with open(self.save_dir / "page.html", "w") as f:
            f.write(
                self.driver.execute_script("return document.documentElement.outerHTML")
            )
        if show:
            screenshot = Image.open(screen)
            screenshot.show()

    def _check_recaptcha(self) -> None:
        """
        Raise a RuntimeError if page shows a ReCaptcha.

        Raises:
            RuntimeError: if page shows a ReCaptcha.
        """
        try:
            LOGGER.info("Looking for ReCaptcha.")
            WebDriverWait(self.driver, 5).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (
                        By.XPATH,
                        "//iframe[starts-with(@name, 'a-') and starts-with(@src, 'https://www.google.com/recaptcha')]",
                    )
                )
            )
            LOGGER.error("Recaptcha detected.")
            raise RuntimeError("Recaptcha detected.")
        except TimeoutException:
            LOGGER.info("ReCaptcha not found.")
            # no recaptch detected.
            return

    def _refuse_cookies(self) -> None:
        """
        Click on `Reject all` button to refuse cookie policy.
        `Reject all` button either has id W0wltc, or is an input button with
        aria-label='Reject all'.

        Raises:
            TimeoutException: if `Reject all` button cannot be located on page.
        """
        LOGGER.info("Clicking on `Reject All` cookie button.")
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input.searchButton[aria-label='Reject all']")
                )
            ).click()
            return
        except TimeoutException:
            pass

        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "W0wltc"))
            ).click()
            return
        except TimeoutException as e:
            LOGGER.error("Unable to locate `Reject All` cookie button.")
            raise e

    def _click_images_search(self) -> None:
        """
        Click on `Images` link to navigate to Image search.
        """
        # Click on images search button.
        try:
            LOGGER.info("Clicking Images search button.")
            time.sleep(1 + random.random())
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.LINK_TEXT, settings.IMAGES_LINK_TEXT))
            ).click()
            return
        except TimeoutException as e:
            LOGGER.error("Unable to locate `Image` link.")
            raise e

    def _validate_image_url(
        self,
        url: ImageUrl,
        keywords: list[str],
        min_res: tuple[int, int] | None = None,
        max_res: tuple[int, int] | None = None,
    ) -> bool:
        """
        Validate an ImageUrl.

        Args:
            url (ImageUrl): the image url to check.
            keywords (list[str]): keywords to avoid in image url or title
            min_res (tuple[int, int] | None, optional): minimum resolution.
                Defaults to None.
            max_res (tuple[int, int] | None, optional): maximum resolution.
                Defaults to None.

        Returns:
            bool: True if image url is valid (has url and title and is
                not already in self.urls)
        """
        if url.title is None or url.url is None or url in self.urls:
            return False

        for kw in keywords:
            if kw.lower() in url.url.lower() or kw.lower() in url.title.lower():
                return False

        if min_res is not None or max_res is not None:
            return url.check_dimensions(min_res, max_res)

        return True

    def _extract_image_url(self) -> ImageUrl | None:
        """
        Look for a valid image tag in the page after having clicked on a
        thumbnail. A valid image tag has one of the known classes, and points
        to a url which isn't of the type https://encrypted-tbn0.gstatic.com

        Returns:
            ImageUrl | None: a valid ImageUrl or None if not found.
        """
        for class_name in settings.IMAGE_CLASSES:
            for image in self.driver.find_elements(By.CLASS_NAME, class_name):
                url = image.get_attribute("src")
                if url is not None and "http" in url and "encrypted" not in url:
                    return ImageUrl(image.get_attribute("alt"), url)
        return None

    def _scroll_through_thumbnails(
        self,
        thumbnails: list[WebElement],
        limit: int,
        urls: set[ImageUrl],
        keywords: list[str],
        min_res: tuple[int, int] | None = None,
        max_res: tuple[int, int] | None = None,
    ):
        """
        Loop through the given list of thumbnails, clicking on each one to reveal the
        source image and extract its url.

        Args:
            thumbnails (list[WebElement]): the list of thumbnails to click.
            limit (int): the maximum number of image urls to extract.
            urls (set[ImageUrl]): the set of collected image urls.
            keywords (list[str]): keywords to avoid in image url or title.
            min_res (tuple[int, int] | None, optional): minimum resolution.
                Defaults to None.
            max_res (tuple[int, int] | None, optional): maximum resolution.
                Defaults to None.
        """
        # make sure first thumbnail is into view
        if len(thumbnails) > 0:
            thumbnails[0].location_once_scrolled_into_view

        # try to click on every new thumbnail to get the real image behind it
        for thumbnail in thumbnails:
            try:
                # Using EC.element_to_be_clickable will scroll down to the element
                # (the element needs to be in the viewport to be clickable).
                # This is important as scrolling down will load more results
                # on the page.
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(thumbnail)
                ).click()
                time.sleep(0.5 + random.random())
            except Exception:
                LOGGER.warning(
                    f"Exception scrolling to thumbnail {thumbnail}", exc_info=True
                )
                continue

            url = self._extract_image_url()
            if url is None or not self._validate_image_url(
                url, keywords, min_res, max_res
            ):
                continue

            urls.add(url)
            LOGGER.info(url)

            if len(urls) >= limit:
                break

    def _gather_urls(
        self,
        limit: int,
        skip: int,
        keywords: list[str],
        min_res: tuple[int, int] | None = None,
        max_res: tuple[int, int] | None = None,
    ) -> set[ImageUrl]:
        """
        Gather image urls from the results page by clicking on each thumbnail. Clicking
        on a thumbnail will display the source image on the side panel, allowing us to
        get its url.

        Args:
            limit (int): the maximum limit of image urls to fetch.
            skip (int): number of results to skip.
            keywords (list[str]): keywords to avoid in image url or title
            min_res (tuple[int, int] | None, optional): minimum resolution.
                Defaults to None.
            max_res (tuple[int, int] | None, optional): maximum resolution.
                Defaults to None.

        Returns:
            set[ImageUrl]: a set of ImageUrls
        """
        LOGGER.info("Gathering image urls.")
        time.sleep(2 + random.random())
        # Loop through all the thumbnails, stopping when we found enough images or
        # when results are exhausted.
        urls: set[ImageUrl] = set()
        seen_thumbnails = 0
        new_results = True
        while len(urls) < limit and new_results:
            # Fetch thumbnails
            thumbnails = self.driver.find_elements(
                By.CSS_SELECTOR, settings.THUMBNAIL_DIV_SELECTOR
            )

            # Check that we have new results (thumbnails not clicked on already)
            new_results = len(thumbnails) - seen_thumbnails > 0
            LOGGER.info(f"Found {len(thumbnails) - seen_thumbnails} thumbnails.")

            # Skip ahead to more results if required.
            if skip > 0 and skip > len(thumbnails):
                LOGGER.info("Skipping ahead.")
                # scroll to last thumbnail
                thumbnails[-1].location_once_scrolled_into_view
                time.sleep(0.5 + random.random())
                seen_thumbnails = len(thumbnails)
                continue

            # Scroll through thumbnails, clicking on them to get the real image urls
            to_scroll = thumbnails[max(seen_thumbnails, skip) :]
            self._scroll_through_thumbnails(
                to_scroll,
                limit=limit,
                urls=urls,
                keywords=keywords,
                min_res=min_res,
                max_res=max_res,
            )

            # Keep track of thumbnails already seen
            seen_thumbnails = len(thumbnails)

        LOGGER.info(f"Done gathering image urls. Found {len(urls)} new image urls.")
        return urls

    def get_image_urls(
        self,
        query: str,
        limit: int = 50,
        skip: int = 0,
        keywords: list[str] = [],
        min_res: tuple[int, int] | None = None,
        max_res: tuple[int, int] | None = None,
    ) -> set[ImageUrl]:
        """
        Main method for GoogleImageScraper. Search google for the `query` and loop
        through image results, clicking on thumbnails to extract the source image urls.
        Scraped image urls are saved to disk in self.urls_file in the self.save_dir
        directory.

        Args:
            query (str): the search query.
            limit (int, optional): the maximum limit of image urls to fetch.
                Defaults to 50.
            skip (int, optional): number of results to skip. Defaults to 0.
            keywords (list[str], optional): keywords to avoid in image url or title.
                Defaults to [].
            min_res (tuple[int, int] | None, optional): minimum resolution.
                Defaults to None.
            max_res (tuple[int, int] | None, optional): maximum resolution.
                Defaults to None.

        Returns:
            set[ImageUrl]: the collected image urls.
        """
        try:
            self._log_search(query, limit, skip, keywords, min_res, max_res)
            self.driver.get(f"https://www.google.com/search?q={query}")
            time.sleep(1 + random.random())

            self._check_recaptcha()
            self._refuse_cookies()
            self._click_images_search()
            urls = self._gather_urls(limit, skip, keywords, min_res, max_res)
            self.urls |= urls
            self._save_urls(self.urls)

            self._log_page()
            return urls
        except Exception:
            LOGGER.error("An exception occured while scraping.", exc_info=True)
            self._log_page()

        return set()

    def _log_search(
        self,
        query: str,
        limit: int = 50,
        skip: int = 0,
        keywords: list[str] = [],
        min_res: tuple[int, int] | None = None,
        max_res: tuple[int, int] | None = None,
    ):
        msg = [
            (
                f"Searching images for '{query}'. Max {limit} new urls ({skip} skipped). "
                f"{len(self.urls)} urls already scraped."
            )
        ]
        if keywords:
            msg.append(f"Excluding keywords {keywords}.")
        if min_res:
            msg.append(f"Min resolution {min_res}.")
        if max_res:
            msg.append(f"Min resolution {max_res}.")
        LOGGER.info("\n".join(msg))
