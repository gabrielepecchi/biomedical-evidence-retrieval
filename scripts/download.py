"""
Download clinical trial pages from the ClinicalTrials.gov V2 API.

Fetches all pages for a condition-focused query (Parkinson disease) and
saves each raw JSON response to data/raw/. Parsing happens in ingest.py.
"""

import json
from pathlib import Path

import requests

BASE_URL: str = "https://clinicaltrials.gov/api/v2/studies"
RAW_DATA_DIR: Path = Path("data") / "raw"
REQUEST_TIMEOUT: int = 30


def fetch_page(params: dict) -> dict:
    """Fetch one page from the API and return the parsed JSON response."""
    response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def save_page(data: dict, page_number: int) -> Path:
    """Write one JSON response dict to data/raw/page_NNN.json."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DATA_DIR / f"page_{page_number:03d}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def download_all_pages() -> None:
    """
    Page through the API and save every response to disk.

    Starts with a condition filter for Parkinson disease and follows
    nextPageToken until no further pages are available.
    """
    params: dict = {
        "query.cond": "Parkinson disease",
        "pageSize": 100,
        "format": "json",
    }

    page_number = 1

    while True:
        print(f"Fetching page {page_number:03d} ...")
        data = fetch_page(params)

        studies = data.get("studies", [])
        saved_path = save_page(data, page_number)
        print(f"  Saved {saved_path} — {len(studies)} record(s)")

        next_token = data.get("nextPageToken")
        if not next_token:
            print("No further pages found. Download complete.")
            break

        params["pageToken"] = next_token
        page_number += 1

    print(f"\nTotal pages downloaded: {page_number}")


def main() -> None:
    download_all_pages()


if __name__ == "__main__":
    main()
