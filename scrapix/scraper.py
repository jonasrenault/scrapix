import logging
import random
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import PIL
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Image:
    title: str | None
    url: str


class GoogleImageScraper:

    def __init__(self, save_dir: Path, headless: bool = False):
        self.headless = headless

        self.save_dir = save_dir
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Saving results to [bold blue]{self.save_dir}[/].")

        self._setup_webdriver()

    def _setup_webdriver(self):
        self.options = Options()
        if self.headless:
            self.options.add_argument("--headless")

        # Set random user agent
        self.user_agent = UserAgent(
            os=["Android"], platforms=["mobile"], min_version=120.0
        ).random
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
            screenshot = PIL.Image.open(screen)
            screenshot.show()

    def _check_recaptcha(self) -> None:
        """
        Check if page shows a ReCaptcha.

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
        LOGGER.info("Clicking on `Reject All` cookie button...")
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
            LOGGER.info("Clicking Images search button")
            time.sleep(1 + random.random())
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Images"))
            ).click()
            return
        except TimeoutException as e:
            LOGGER.error("Unable to locate `Image` link.")
            raise e

    def _extract_image_url(self) -> Image | None:
        for class_name in ["n3VNCb", "iPVvYb", "r48jcc", "pT0Scc"]:
            for image in self.driver.find_elements(By.CLASS_NAME, class_name):
                url = image.get_attribute("src")
                if url and "http" in url and "encrypted" not in url:
                    image_url = Image(image.get_attribute("alt"), url)
                    return image_url
        return None

    def _validate_image_url(self, image: Image):
        if image.title is None or image.url is None:
            return False
        return True

    def _gather_urls(self, limit: int) -> set[Image]:
        LOGGER.info("Gathering image urls.")
        time.sleep(2 + random.random())
        # Loop through all the thumbnails, stopping when we found enough images or
        # when results are exhausted.
        images: set[Image] = set()
        visited_thumbnails: list[WebElement] = []
        new_results = True
        while len(images) < limit and new_results:
            # Fetch thumbnails
            thumbnails = self.driver.find_elements(
                By.XPATH,
                "//img[starts-with(@id, 'dimg_') and starts-with(@src, 'https')]",
            )

            # Check that we have new results
            new_results = len(thumbnails) - len(visited_thumbnails) > 0
            LOGGER.info(f"Found {len(thumbnails) - len(visited_thumbnails)} thumbnails..")

            # try to click on every new thumbnail to get the real image behind it
            for thumbnail in tqdm(thumbnails[len(visited_thumbnails) :]):
                try:
                    # Using EC.element_to_be_clickable will scroll down to the element
                    # (the element needs to be in the viewport to be clickable).
                    # This is important as scrolling down will load more results
                    # on the page.
                    WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(thumbnail)
                    )
                    time.sleep(0.5 + random.random())
                except Exception:
                    LOGGER.warning(
                        f"Exception scrolling to thumbnail {thumbnail}", exc_info=True
                    )
                    continue

                url = thumbnail.get_attribute("src")
                if url is None:
                    continue

                image = Image(thumbnail.get_attribute("alt"), url)
                if self._validate_image_url(image):
                    images.add(image)
                    LOGGER.info(f"Added {image}")

                if len(images) >= limit:
                    break

            # Keep track of thumbnails already seen
            visited_thumbnails = thumbnails
        return images

    def get_image_urls(
        self,
        query: str,
        limit: int = 10,
        min_resolution: tuple[int, int] = (640, 300),
        max_resolution: tuple[int, int] = (2048, 2048),
    ) -> dict[str, str]:
        try:
            # First, do a regular search for the term, and refuse cookie policy popup.
            LOGGER.info(f"Searching images for {query}")
            self.driver.get(f"https://www.google.com/search?q={query}")
            time.sleep(1 + random.random())

            self._check_recaptcha()
            self._refuse_cookies()
            self._click_images_search()
            self._gather_urls(limit)

            self._log_page()
        except Exception:
            LOGGER.error(
                f"An exception occured while scraping:\n{traceback.format_exc()}"
            )
            self._log_page()

        return {}
