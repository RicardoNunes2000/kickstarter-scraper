# Kickstarter Scraper

This Python project provides a tool to scrape information about Kickstarter creators and their projects. It uses the `requests`, `BeautifulSoup`, and `pydantic` libraries to fetch and parse data from Kickstarter profiles.

## Features

- Fetch information about a Kickstarter creator, including:
  - Name
  - City and state
  - Join date
  - Backer favorite status
  - Superbacker status
  - Number of backed projects
  - Description

- Fetch information about projects created by the Kickstarter creator, including:
  - Project title
  - Status
  - Percentage of funding
  - Categories
  - Project URL

## Requirements

- Python 3.x
- Requests
- BeautifulSoup4
- Pydantic

You can install the required libraries using pip:

```bash
pip install requests beautifulsoup4 pydantic