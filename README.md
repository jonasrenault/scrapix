# 🖼️ Scrapix - Smart, fast, and simple image scraper for Google Search

Scrapix is an automated image scraper designed to collect pictures from Google Search based on user-defined queries. It streamlines the process of fetching, filtering, and storing image results for use in datasets, research, or creative projects.

## Documentation

**The documentation for Scrapix is available [here](https://jonasrenault.github.io/scrapix/).**

## Install

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

### CLI

When you install Scrapix in a virtual environment, it creates a CLI script called `scrapix`. Run

```bash
scrapix --help
```

to see the various commands available (or take a look at the [documentation](https://jonasrenault.github.io/scrapix/) for examples).
