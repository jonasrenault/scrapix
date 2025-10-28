from pathlib import Path

import responses

from scrapix.urls import ImageUrl, get_filename

ROOT_DIR = Path(__file__).parent.parent


def test_urls_can_be_created():
    url = "http://mycustomimageurl.com"
    title = "A very nice image"

    image_url = ImageUrl(title, url)
    assert image_url.title == title
    assert image_url.url == url


def test_get_filename():
    url = "https://cdn.store-factory.com/www.reptile-paradise.fr/content/product%20image.jpg?v=1720559822"
    filename = get_filename(url)
    assert filename == "product image.jpg"

    url = "https://www.imagesdoc.com/wp-content/uploads/sites/33/2018/10/AdobeStock_67152957-e1540977088518.jpeg"
    filename = get_filename(url)
    assert filename == "AdobeStock_67152957-e1540977088518.jpeg"


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
