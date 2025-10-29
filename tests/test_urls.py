from pathlib import Path
from unittest.mock import mock_open, patch

import responses

from scrapix.urls import ImageUrl, read_urls

ROOT_DIR = Path(__file__).parent.parent


def test_urls_can_be_created():
    url = "http://mycustomimageurl.com"
    title = "A very nice image"

    image_url = ImageUrl(title, url)
    assert image_url.title == title
    assert image_url.url == url


def test_read_urls():
    title1 = "lorem ipsum"
    title2 = "dolor sit"
    url1 = "https://i.pinimg.com/ab3034f03fea4afbfc045dd32d3979af.jpg"
    url2 = "https://cdn.britannica.com/52/Escargot-cooked.jpg"
    URLS = f'[{{"title": "{title1}", "url": "{url1}"}},{{"title": "{title2}", "url": "{url2}"}}]'  # noqa: E501
    m = mock_open(read_data=URLS)

    file = Path("urls.json")
    with patch("builtins.open", m):
        urls = read_urls(file)

    m.assert_called_once_with(file, "r")
    assert len(urls) == 2
    assert ImageUrl(title1, url1) in urls
    assert ImageUrl(title2, url2) in urls


def test_get_filename():
    url = ImageUrl(
        None,
        "https://cdn.store-factory.com/www.reptile-paradise.fr/content/product%20image.jpg?v=1720559822",
    )
    assert url.filename == "product image.jpg"

    url = ImageUrl(
        None,
        "https://www.imagesdoc.com/wp-content/uploads/sites/33/2018/10/AdobeStock_67152957-e1540977088518.jpeg",
    )
    assert url.filename == "AdobeStock_67152957-e1540977088518.jpeg"


@responses.activate
def test_check_dimensions():
    with open(ROOT_DIR / "resources" / "images" / "scraper.webp", "rb") as image:
        mock_url = "http://example.org/test/test-image.jpg"
        responses.get(
            mock_url,
            body=image.read(),
            status=200,
            content_type="image/jpeg",
            stream=True,
        )

    image_url = ImageUrl("A nice scraper", mock_url)

    # mock image has dimension 452 x 452
    assert image_url.check_dimensions((20, 20), (1200, 1200))
    assert not image_url.check_dimensions((640, 640), (1200, 1200))
    assert not image_url.check_dimensions((20, 20), (320, 320))
