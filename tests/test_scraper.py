from pathlib import Path

import pytest

from scrapix.scraper import GoogleImageScraper


@pytest.mark.ci
@pytest.mark.asyncio
async def test_headless_google_scraping(tmp_path: Path):
    urls_file = "my_duck_urls.json"
    scraper = await GoogleImageScraper.create(
        tmp_path, headless=True, urls_file=urls_file
    )
    urls = await scraper.get_image_urls(
        "duck", limit=2, skip=0, keywords=["rubber", "toy"]
    )
    assert len(urls) == 2
    assert tmp_path.joinpath(urls_file).exists()
