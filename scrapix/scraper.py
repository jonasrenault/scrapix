import logging
import random
import time
import traceback
from pathlib import Path

from fake_useragent import UserAgent
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOGGER = logging.getLogger(__name__)


class GoogleImageScraper:

    def __init__(self, save_dir: Path, headless: bool = False):
        self.headless = headless

        self.save_dir = save_dir
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Saving results to [bold blue]{self.save_dir}[/].")

        self._setup_webdriver()

    def _setup_webdriver(
        self,
    ):
        self.options = Options()
        if self.headless:
            self.options.add_argument("--headless")

        # Set random user agent
        self.user_agent = UserAgent(os=["Android"], platforms=["mobile", "tablet"]).random
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
        screen = self.save_dir / "screenshot.png"
        self.driver.save_screenshot(screen)
        with open(self.save_dir / "page.html", "w") as f:
            f.write(
                self.driver.execute_script("return document.documentElement.outerHTML")
            )
        if show:
            screenshot = Image.open(screen)
            screenshot.show()

    def _check_recaptcha(
        self,
    ):
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

    def _refuse_cookies(
        self,
    ):
        """
        Refuse cookie policy. `Reject all` button either has id W0wltc, or is
        an input button with aria-label='Reject all'.
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
            LOGGER.warning("Unable to locate `Reject All` cookie button.")
            raise e

    def _click_images_search(self):
        # Click on images search button.
        time.sleep(1 + random.random())
        LOGGER.info("Clicking Images search button")
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Images"))
        ).click()

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

            self._log_page()
        except Exception:
            LOGGER.error(
                f"An exception occured while scraping:\n{traceback.format_exc()}"
            )
            self._log_page()

        return {}
