"""
CodeAlpha Data Analytics Internship - Task 1: Web Scraping
============================================================
Project theme: Movie Analytics (feeds into Tasks 2, 3 and 4)

What this script does
----------------------
1. Scrapes the Wikipedia "List of highest-grossing films" table using
   requests + BeautifulSoup (classic web scraping, no anti-bot issues,
   Wikipedia is scrape-friendly for reasonable, low-frequency use).
2. Enriches every movie with richer metadata (genre, IMDb rating, runtime,
   director, language, country, votes, box office) via the free OMDb API.
   This turns a bare "title + gross" list into a dataset that's actually
   rich enough for interesting EDA and visualizations later.
3. Saves a clean CSV to data/movies_raw.csv and a checkpoint file so you
   never lose progress if the run is interrupted.

Before you run it
------------------
1. pip install -r requirements.txt
2. Get a FREE OMDb API key (instant, just an email): https://www.omdbapi.com/apikey.aspx
3. Set it as an environment variable so you never hardcode a secret:
       Windows (PowerShell):  $env:OMDB_API_KEY="yourkeyhere"
       Mac/Linux:              export OMDB_API_KEY="yourkeyhere"
4. Run:  python scrape_movies.py

Why this counts as "web scraping" for the internship task
-----------------------------------------------------------
Step 1 is textbook BeautifulSoup table scraping. Step 2 (API enrichment)
is a bonus skill on top — it shows you can combine multiple data sources
into one clean dataset, which is exactly what real analysts do.
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
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "")  # set this in your environment
HEADERS = {
    # Wikipedia asks bots/scripts to identify themselves - be a good citizen
    "User-Agent": "CodeAlpha-Internship-MovieAnalytics/1.0 (educational project)"
}
RAW_CSV = "data/movies_raw.csv"
CHECKPOINT_EVERY = 20
REQUEST_DELAY_SEC = 0.25  # be polite to the OMDb API


def scrape_highest_grossing_films() -> pd.DataFrame:
    """Scrape the highest-grossing films table from Wikipedia."""
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
        if any("gross" in c for c in cols_lower) and any("title" in c for c in cols_lower):
            target_df = df
            break

    if target_df is None:
        raise RuntimeError(
            "Could not find the highest-grossing films table. "
            "Wikipedia may have changed its page layout - inspect the page "
            "manually and update the column-matching logic above."
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

    # Clean title text (footnote markers, reference numbers)
    target_df["title"] = (
        target_df["title"].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip()
    )

    keep_cols = [c for c in ["rank", "peak", "title", "worldwide_gross", "year"] if c in target_df.columns]
    target_df = target_df[keep_cols].drop_duplicates(subset="title").reset_index(drop=True)

    print(f"Scraped {len(target_df)} movies from Wikipedia.")
    return target_df


def clean_title_for_query(title: str) -> str:
    """Strip characters that commonly break OMDb title matching."""
    title = re.sub(r"\(.*?\)", "", title)  # remove parenthetical notes
    return title.strip()


def fetch_omdb_details(title: str, year: str = None) -> dict:
    """Query OMDb for one movie. Falls back to a title-only search if the
    title+year lookup fails (OMDb is picky about exact titles/years)."""
    if not OMDB_API_KEY:
        raise RuntimeError(
            "OMDB_API_KEY is not set. Get a free key at "
            "https://www.omdbapi.com/apikey.aspx and set it as an env variable."
        )

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


def enrich_with_omdb(df: pd.DataFrame) -> pd.DataFrame:
    """Loop over the scraped movies and enrich each with OMDb metadata,
    saving a checkpoint periodically so progress is never lost."""
    enriched_rows = []
    os.makedirs("data", exist_ok=True)

    for i, row in df.iterrows():
        details = fetch_omdb_details(row["title"], row.get("year"))
        merged = {**row.to_dict(), **details}
        enriched_rows.append(merged)

        if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(df):
            pd.DataFrame(enriched_rows).to_csv(RAW_CSV, index=False)
            print(f"  ...{i + 1}/{len(df)} movies processed (checkpoint saved)")

        time.sleep(REQUEST_DELAY_SEC)

    return pd.DataFrame(enriched_rows)


def main():
    base_df = scrape_highest_grossing_films()
    print("Enriching with OMDb data (this can take a few minutes for 200+ titles)...")
    full_df = enrich_with_omdb(base_df)
    os.makedirs("data", exist_ok=True)
    full_df.to_csv(RAW_CSV, index=False)
    print(f"\nDone. Saved {len(full_df)} enriched movie records to {RAW_CSV}")
    print(full_df.head())


if __name__ == "__main__":
    main()
