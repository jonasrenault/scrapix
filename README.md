# 🖼️ Scrapix - Smart, fast, and simple image scraper for Google Image Search

Scrapix is an automated image scraper designed to collect pictures from Google Image Search based on user-defined queries. It streamlines the process of fetching, filtering, and storing image results for use in datasets, research, or creative projects.

## Installation

Scrapix requires a recent version of python: ![python_version](https://img.shields.io/badge/Python-%3E=3.12-blue).

### Install from github

Clone the repository and install the project in your python environment, either using `pip`

```bash
git clone https://github.com/jonasrenault/scrapix.git
cd scrapix
pip install --editable .
```

or [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/jonasrenault/scrapix.git
cd scrapix
uv sync
```

## Usage

### Command-line

When you install Scrapix in a virtual environment, it creates a CLI script called `scrapix`. Run

```bash
scrapix --help
```

to see the various commands available. The main command is `scrape` which will search for images matching a query on Google Search, save the image urls in a file on disk, and optionally download the images on disk too.

For example, the following command

```bash
scrapix scrape duck -l 5 --min 640 640 -k rubber -k toy
```

will search for 5 images of `duck`, only keeping images with a minimum resolution of `640x640` pixels, and excluding images which may contain the words `rubber` or `toy` in their url or title.

The results will be saved by default in `~/.cache/scrapix/{query}` (can be changed with the `--dir` option). It will save a JSON file containing the scraped image urls and titles, and will also download the images if the `--download` flag is set (it's on by default). Here are the image urls that the above command will save in the file `~/.cache/scrapix/duck/urls.json`:

```json
[
  {
    "title": "Mallard Duck | National Geographic Kids",
    "url": "https://i.natgeofe.com/k/7ce14b7f-df35-4881-95ae-650bce0adf4d/mallard-male-standing_square.jpg"
  },
  {
    "title": "Ten Things You Didn't Know About Ducks",
    "url": "https://assets.farmsanctuary.org/content/uploads/2025/06/17071818/2021_04-28_FSNY_Macka_and_Milo_ducks_DSC_3924_CREDIT_Farm_Sanctuary-1600x1068.jpg"
  },
  {
    "title": "Mallard Duck | National Geographic Kids",
    "url": "https://i.natgeofe.com/k/327b01e8-be2e-4694-9ae9-ae7837bd8aea/mallard-male-swimming.jpg"
  },
  {
    "title": "10 Facts About Ducks - FOUR PAWS International - Animal Welfare Organisation",
    "url": "https://media.4-paws.org/a/f/4/7/af47ae6aa55812faa4d7fd857a6e283a8c8226bc/VIER%20PFOTEN_2019-07-18_013-2890x2000-1920x1329.jpg"
  },
  {
    "title": "Duck - Wikipedia",
    "url": "https://upload.wikimedia.org/wikipedia/commons/b/bf/Bucephala-albeola-010.jpg"
  }
]
```

#### Arguments

```bash
scrapix scrape --help

 Usage: scrapix scrape [OPTIONS] QUERY

╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    query      TEXT  Search query. [required]                                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --dir       -d                   DIRECTORY             Save directory.   [default: ~/.cache/scrapix]                        │
│ --limit     -l                   INTEGER               Max number of images to download. [default: 10]                      │
│ --skip      -s                   INTEGER               Number of results to skip. [default: 0]                              │
│ --keywords  -k                   TEXT                  Keywords to exclude.                                                 │
│ --min                            <INTEGER INTEGER>...  Minimum resolution of images.                                        │
│ --max                            <INTEGER INTEGER>...  Maximum resolution of images.                                        │
│ --download      --no-download                          Save images on disk after scraping the urls. [default: download]     │
│ --force         --no-force                             Force redownload of images already present on disk.                  │
│                                                        [default: no-force]                                                  │
│ --help                                                 Show this message and exit.                                          │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Python

```python
from pathlib import Path
from scrapix import GoogleImageScraper

save_dir = Path("./images")
scraper = GoogleImageScraper(save_dir)
# search for images and return a set of image urls
urls = scraper.get_image_urls(query="duck", limit=10, keywords=["rubber", "toy"], min_res=(640, 640), max_res=(1200, 1200))

# download each image to disk
for url in urls:
    url.download(save_dir=save_dir)
```
