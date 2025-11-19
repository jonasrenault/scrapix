from pathlib import Path

import pytest

from scrapix.scraper import GoogleImageScraper


@pytest.mark.asyncio
async def test_headless_google_scraping(tmp_path: Path):
    scraper = await GoogleImageScraper.create(tmp_path, True)
    urls = await scraper.get_image_urls(
        "duck", limit=2, skip=0, keywords=["rubber", "toy"]
    )
    assert len(urls) == 2
