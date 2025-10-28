from scrapix.urls import ImageUrl


def test_urls_can_be_created():
    url = "http://mycustomimageurl.com"
    title = "A very nice image"

    image_url = ImageUrl(title, url)
    assert image_url.title == title
    assert image_url.url == url
