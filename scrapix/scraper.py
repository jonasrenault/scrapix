import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any

from PIL import Image
from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.browser.tab import Tab
from pydoll.elements.web_element import WebElement
from pydoll.exceptions import ElementNotFound

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

    @classmethod
    async def create(
        cls,
        save_dir: Path,
        headless: bool = False,
        urls_file: str = "urls.json",
        force: bool = False,
    ) -> "GoogleImageScraper":
        self = cls(save_dir, headless, urls_file, force)
        await self._setup_options()
        return self

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

    async def _setup_options(self):
        """
        Setup the browser configuration with custom options.
        """
        # Extract the default browser profile
        options = ChromiumOptions()
        options.add_argument("--headless=new")
        async with Chrome(options=options) as browser:
            tab = await browser.start()
            self.profile = await self.collect_browser_profile(tab)
            self.profile["userAgent"] = self.profile["userAgent"].replace("Headless", "")
            LOGGER.info(f"Browser profile:\n{json.dumps(self.profile, indent=2)}")

        # Create browser configuration with correct options
        self.options = ChromiumOptions()

        if self.headless:
            self.options.add_argument("--headless=new")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--disable-gpu")

        # 1. User-Agent
        self.options.add_argument(f'--user-agent={self.profile["userAgent"]}')
        # 2. Window size (screen dimensions)
        screen = self.profile["screen"]
        self.options.add_argument(f'--window-size={screen["width"]},{screen["height"]}')
        # 3. Device scale factor (for high-DPI displays)
        if screen.get("deviceScaleFactor", 1.0) != 1.0:
            self.options.add_argument(
                f'--device-scale-factor={screen["deviceScaleFactor"]}'
            )

    async def collect_browser_profile(self, tab: Tab) -> dict[str, Any]:
        result = await tab.execute_script(
            """return {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                languages: navigator.languages,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                maxTouchPoints: navigator.maxTouchPoints,

                screen: {
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                },

                // Window
                window: {
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    devicePixelRatio: window.devicePixelRatio,
                },

                // Timezone
                timezone: {
                    offset: new Date().getTimezoneOffset(),
                    name: Intl.DateTimeFormat().resolvedOptions().timeZone,
                },

                // Plugins (legacy, but still checked)
                plugins: Array.from(navigator.plugins).map(p => ({
                    name: p.name,
                    description: p.description,
                })),

                // User Agent Data (Chrome)
                userAgentData: navigator.userAgentData ? {
                    brands: navigator.userAgentData.brands,
                    mobile: navigator.userAgentData.mobile,
                    platform: navigator.userAgentData.platform,
                } : null,
            };""",
            return_by_value=True,
        )
        if "value" not in result["result"]["result"]:
            raise RuntimeError("Unable to retrieve browser profile.")
        return result["result"]["result"]["value"]

    def __str__(self) -> str:
        repr_str = (
            f"{self.__class__.__name__}: Headless={self.headless}, "
            f"Options: {self.options}"
        )
        return repr_str

    async def _log_page(self, tab: Tab, show: bool = False):
        """
        Log the current page by saving a screenshot and the page source to disk.

        Args:
            tab (Tab): the current browser tab.
            show (bool, optional): show the screenshot. Defaults to False.
        """
        screen = self.save_dir / "screenshot.png"
        await tab.take_screenshot(screen)
        html = await tab.page_source
        with open(self.save_dir / "page.html", "w") as f:
            f.write(html)
        if show:
            screenshot = Image.open(screen)
            screenshot.show()

    async def _check_recaptcha(self, tab: Tab) -> bool:
        """
        Raise a RuntimeError if page shows a ReCaptcha.

        Args:
            tab (Tab): the current browser tab.

        Raises:
            RuntimeError: if page shows a ReCaptcha.

        Returns:
            bool: False if no recaptcha was found.
        """
        LOGGER.info("Looking for ReCaptcha.")
        has_recaptcha = await tab.query(
            "//iframe[starts-with(@name, 'a-') and starts-with(@src, 'https://www.google.com/recaptcha')]",
            timeout=1,
            raise_exc=False,
        )
        if has_recaptcha:
            raise RuntimeError("Recaptcha detected.")
        LOGGER.info("ReCaptcha not found.")
        return False

    async def _refuse_cookies(self, tab: Tab):
        """
        Click on `Reject all` button to refuse cookie policy.
        `Reject all` button either has id W0wltc.

        Args:
            tab (Tab): the current browser tab.
        """
        LOGGER.info("Clicking on `Reject All` cookie button.")
        reject_btn = await tab.find(
            tag_name="button",
            id="W0wltc",
            timeout=2,
            raise_exc=False,
            find_all=False,
        )
        if reject_btn:
            await reject_btn.click()
        else:
            LOGGER.info("Unable to locate `Reject All` cookie button.")

    async def _click_images_search(self, tab: Tab):
        """
        Click on `Images` link to navigate to Image search.

        Args:
            tab (Tab): the current browser tab.

        Raises:
            ElementNotFound: if Images link cannot be located on page.
        """
        # Click on images search button.
        LOGGER.info("Clicking Images search button.")
        images_link = await tab.find(
            text=settings.IMAGES_LINK_TEXT, timeout=2, raise_exc=False, find_all=False
        )
        if images_link:
            await images_link.click()
        else:
            LOGGER.error("Unable to locate `Image` link.")
            raise ElementNotFound("Unable to locate `Image` link.")

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

    async def _extract_image_url(self, tab: Tab) -> ImageUrl | None:
        """
        Look for a valid image tag in the page after having clicked on a
        thumbnail. A valid image tag has one of the known classes, and points
        to a url which isn't of the type https://encrypted-tbn0.gstatic.com

        Args:
            tab (Tab): the current browser tab.

        Returns:
            ImageUrl | None: a valid ImageUrl or None if not found.
        """
        for class_name in settings.IMAGE_CLASSES:
            image = await tab.find(
                tag_name="img", class_name=class_name, raise_exc=False, find_all=False
            )
            if image is not None:
                url = image.get_attribute("src")
                if url is not None and "http" in url and "encrypted" not in url:
                    return ImageUrl(image.get_attribute("alt"), url)
        return None

    async def _scroll_through_thumbnails(
        self,
        tab: Tab,
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
            tab (Tab): the current browser tab.
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
            await thumbnails[0].scroll_into_view()

        # try to click on every new thumbnail to get the real image behind it
        for thumbnail in thumbnails:
            try:
                await thumbnail.click()
                await asyncio.sleep(random.uniform(0.5, 2.0))
            except Exception:
                LOGGER.warning(
                    f"Exception clicking on thumbnail {thumbnail}", exc_info=True
                )
                continue

            url = await self._extract_image_url(tab)
            if url is None or not self._validate_image_url(
                url, keywords, min_res, max_res
            ):
                continue

            urls.add(url)
            LOGGER.info(url)

            if len(urls) >= limit:
                break

    async def _gather_urls(
        self,
        tab: Tab,
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
            tab (Tab): the current browser tab.
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
        await asyncio.sleep(random.uniform(1.0, 2.0))
        # Loop through all the thumbnails, stopping when we found enough images or
        # when results are exhausted.
        urls: set[ImageUrl] = set()
        seen_thumbnails = 0
        new_results = True
        while len(urls) < limit and new_results:
            # Fetch thumbnails
            thumbnails = await tab.find(
                tag_name="div", class_name=settings.THUMBNAIL_DIV_CLASS, find_all=True
            )

            # Check that we have new results (thumbnails not clicked on already)
            new_results = len(thumbnails) - seen_thumbnails > 0
            LOGGER.info(f"Found {len(thumbnails) - seen_thumbnails} thumbnails.")

            # Skip ahead to more results if required.
            if skip > 0 and skip > len(thumbnails):
                LOGGER.info("Skipping ahead.")
                # scroll to last thumbnail
                await thumbnails[-1].scroll_into_view()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                seen_thumbnails = len(thumbnails)
                continue

            # Scroll through thumbnails, clicking on them to get the real image urls
            to_scroll = thumbnails[max(seen_thumbnails, skip) :]
            await self._scroll_through_thumbnails(
                tab,
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

    async def get_image_urls(
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
        Scraped image urls are saved to disk in `self.urls_file` in the `self.save_dir`
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
        self._log_search(query, limit, skip, keywords, min_res, max_res)
        async with Chrome(options=self.options) as browser:
            tab = await browser.start()
            await tab.go_to(f"https://www.google.com/search?q={query}", timeout=30)
            await asyncio.sleep(random.uniform(1.0, 3.0))
            try:
                await self._check_recaptcha(tab)
                await self._refuse_cookies(tab)
                await self._click_images_search(tab)
                urls = await self._gather_urls(
                    tab, limit, skip, keywords, min_res, max_res
                )
                self.urls |= urls
                self._save_urls(self.urls)

                await self._log_page(tab)
                return urls
            except Exception as e:
                LOGGER.error("An exception occured while scraping.", exc_info=True)
                await self._log_page(tab)
                raise e

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
