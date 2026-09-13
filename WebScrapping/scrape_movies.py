"""
Task 1: Web Scraping - Movie Analytics project
CodeAlpha Data Analytics Internship

Grabs the highest-grossing films table off Wikipedia, then fills in the
extra details (genre, rating, runtime, director...) using the OMDb API,
since Wikipedia's table alone is pretty bare.

Steps to run:
1. pip install -r requirements.txt
2. python scrape_movies.py

Your OMDb key is already set below as a fallback, but it's better practice
to keep it out of code that goes to GitHub. If you want to do that properly,
set it as an environment variable instead and it'll be picked up automatically:
    Windows:     $env:OMDB_API_KEY="your_key"
    Mac/Linux:   export OMDB_API_KEY="your_key"
"""

import os
import re
import time
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_highest-grossing_films"
OMDB_URL = "http://www.omdbapi.com/"

# Uses the env variable if it's set, otherwise falls back to the key below
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "5ad652c0")

HEADERS = {"User-Agent": "CodeAlpha-MovieAnalytics/1.0 (student project)"}
RAW_CSV = "data/movies_raw.csv"
CHECKPOINT_EVERY = 20
REQUEST_DELAY_SEC = 0.25


def scrape_highest_grossing_films():
    """Pull the highest-grossing films table straight off Wikipedia."""
    print(f"Fetching {WIKI_URL} ...")
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", {"class": "wikitable"})

    target_df = None
    for table in tables:
        try:
            df = pd.read_html(str(table))[0]
        except ValueError:
            continue
        # The table we want has a "Worldwide gross" (or similar) column
        cols_lower = [str(c).lower() for c in df.columns]
        # this is the table that has both a title and a gross column
        if any("gross" in c for c in cols_lower) and any("title" in c for c in cols_lower):
            target_df = df
            break

    if target_df is None:
        raise RuntimeError(
            "Couldn't find the right table - Wikipedia might have changed "
            "the page layout. Worth checking the page manually."
        )

    # Normalize column names
    target_df.columns = [re.sub(r"\[.*?\]", "", str(c)).strip() for c in target_df.columns]
    rename_map = {}
    for c in target_df.columns:
        cl = c.lower()
        if "title" in cl:
            rename_map[c] = "title"
        elif "gross" in cl:
            rename_map[c] = "worldwide_gross"
        elif cl == "year":
            rename_map[c] = "year"
        elif "rank" in cl:
            rename_map[c] = "rank"
        elif "peak" in cl:
            rename_map[c] = "peak"
    target_df = target_df.rename(columns=rename_map)

    # strip footnote markers like [1] off the titles
    target_df["title"] = (
        target_df["title"].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip()
    )

    keep_cols = [c for c in ["rank", "peak", "title", "worldwide_gross", "year"] if c in target_df.columns]
    target_df = target_df[keep_cols].drop_duplicates(subset="title").reset_index(drop=True)

    print(f"Scraped {len(target_df)} movies from Wikipedia.")
    return target_df


def clean_title_for_query(title):
    # OMDb chokes on parenthetical notes like "(film)" so strip those out
    title = re.sub(r"\(.*?\)", "", title)
    return title.strip()


def fetch_omdb_details(title, year=None):
    """Look up one movie on OMDb. If title+year doesn't match anything,
    try again without the year - OMDb can be fussy about that."""
    params = {"apikey": OMDB_API_KEY, "t": clean_title_for_query(title), "plot": "short"}
    if year and str(year).strip().isdigit():
        params["y"] = str(year).strip()[:4]

    try:
        r = requests.get(OMDB_URL, params=params, timeout=10)
        data = r.json()
    except (requests.RequestException, json.JSONDecodeError):
        return {}

    if data.get("Response") == "False" and "y" in params:
        # Retry without the year constraint in case OMDb has a different year on file
        params.pop("y")
        try:
            r = requests.get(OMDB_URL, params=params, timeout=10)
            data = r.json()
        except (requests.RequestException, json.JSONDecodeError):
            return {}

    if data.get("Response") == "False":
        return {}

    return {
        "genre": data.get("Genre"),
        "imdb_rating": data.get("imdbRating"),
        "imdb_votes": data.get("imdbVotes"),
        "runtime": data.get("Runtime"),
        "director": data.get("Director"),
        "language": data.get("Language"),
        "country": data.get("Country"),
        "box_office_omdb": data.get("BoxOffice"),
        "awards": data.get("Awards"),
    }


def enrich_with_omdb(df):
    """Go through every movie and add the OMDb details, saving a checkpoint
    every so often so a crash halfway through doesn't lose everything."""
    enriched_rows = []
    os.makedirs("data", exist_ok=True)

    for i, row in df.iterrows():
        details = fetch_omdb_details(row["title"], row.get("year"))
        merged = {**row.to_dict(), **details}
        enriched_rows.append(merged)

        if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(df):
            pd.DataFrame(enriched_rows).to_csv(RAW_CSV, index=False)
            print(f"  ...{i + 1}/{len(df)} done (checkpoint saved)")

        time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(enriched_rows)


def main():
    base_df = scrape_highest_grossing_films()
    print("Enriching with OMDb data, this'll take a few minutes for 200+ titles...")
    full_df = enrich_with_omdb(base_df)
    os.makedirs("data", exist_ok=True)
    full_df.to_csv(RAW_CSV, index=False)
    print(f"\nDone. Saved {len(full_df)} movies to {RAW_CSV}")
    print(full_df.head())


if __name__ == "__main__":
    main()
