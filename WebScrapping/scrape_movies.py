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

    # strip footnote markers like [1] off every column - if left in, a reference
    # number can bleed straight into the digits when we clean the gross figures later
    for col in target_df.columns:
        target_df[col] = (
            target_df[col].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip()
        )

    keep_cols = [c for c in ["rank", "peak", "title", "worldwide_gross", "year"] if c in target_df.columns]
    target_df = target_df[keep_cols].drop_duplicates(subset="title").reset_index(drop=True)

    print(f"Scraped {len(target_df)} movies from Wikipedia.")
    return target_df


def clean_title_for_query(title):
    # OMDb chokes on parenthetical notes like "(film)" so strip those out
    title = re.sub(r"\(.*?\)", "", title)
    return title.strip()


def roman_numeral_variant(title):
    """'Frozen 2' -> 'Frozen II', 'Toy Story 3' -> 'Toy Story III', etc.
    IMDb's official titles almost always use Roman numerals for sequels, which is
    a common cause of OMDb matching the wrong (unrelated) title entirely."""
    numeral_map = {"2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI"}
    match = re.match(r"^(.*)\s([2-6])$", title.strip())
    if not match:
        return None
    base, digit = match.groups()
    return f"{base} {numeral_map[digit]}"


# A movie that made the highest-grossing list of all time will always have a huge
# IMDb vote count. If OMDb hands back a match with way fewer votes than this, it's
# almost certainly the wrong movie (classic trap: "Frozen 2" vs the official "Frozen II").
MIN_PLAUSIBLE_VOTES = 20000


def _omdb_get(params):
    try:
        r = requests.get(OMDB_URL, params={**params, "apikey": OMDB_API_KEY}, timeout=10)
        return r.json()
    except (requests.RequestException, json.JSONDecodeError):
        return {}


def _votes_to_int(votes_str):
    if not votes_str or votes_str == "N/A":
        return 0
    try:
        return int(votes_str.replace(",", ""))
    except ValueError:
        return 0


def _lookup_by_title(title, year=None):
    params = {"t": clean_title_for_query(title), "plot": "short"}
    if year and str(year).strip().isdigit():
        params["y"] = str(year).strip()[:4]

    data = _omdb_get(params)
    if data.get("Response") == "False" and "y" in params:
        # Retry without the year constraint in case OMDb has a different year on file
        params.pop("y")
        data = _omdb_get(params)
    return data


def _lookup_via_search(title, year=None):
    """Fallback: search OMDb instead of guessing the exact title, then pull full
    details for the best-looking candidate (closest year, movie type only)."""
    search_params = {"s": clean_title_for_query(title), "type": "movie"}
    data = _omdb_get(search_params)
    candidates = data.get("Search", []) if data.get("Response") == "True" else []
    if not candidates:
        return {}

    def year_distance(c):
        try:
            return abs(int(c.get("Year", "0")[:4]) - int(str(year)[:4]))
        except (ValueError, TypeError):
            return 99
    candidates.sort(key=year_distance)

    best = candidates[0]
    imdb_id = best.get("imdbID")
    if not imdb_id:
        return {}
    return _omdb_get({"i": imdb_id, "plot": "short"})


def fetch_omdb_details(title, year=None):
    """Look up one movie on OMDb, with sanity checks to catch mismatched titles.
    Order of attempts: exact title -> Roman-numeral variant (Frozen 2 -> Frozen II)
    -> search endpoint. If nothing plausible turns up, we'd rather leave the row
    blank than silently keep a wrong match."""
    data = _lookup_by_title(title, year)

    if data.get("Response") == "False" or _votes_to_int(data.get("imdbVotes")) < MIN_PLAUSIBLE_VOTES:
        variant = roman_numeral_variant(clean_title_for_query(title))
        if variant:
            variant_data = _lookup_by_title(variant, year)
            if _votes_to_int(variant_data.get("imdbVotes")) >= MIN_PLAUSIBLE_VOTES:
                data = variant_data

    if data.get("Response") == "False" or _votes_to_int(data.get("imdbVotes")) < MIN_PLAUSIBLE_VOTES:
        search_data = _lookup_via_search(title, year)
        if _votes_to_int(search_data.get("imdbVotes")) >= MIN_PLAUSIBLE_VOTES:
            data = search_data

    # Still no plausible match after all three attempts. Rather than dropping the
    # row outright (a genuinely recent release can have low votes for real, not
    # because of a mismatch), keep the data but flag it so it's easy to spot and
    # spot-check in the EDA step.
    match_uncertain = _votes_to_int(data.get("imdbVotes")) < MIN_PLAUSIBLE_VOTES

    if data.get("Response") == "False":
        return {}

    return {
        "match_uncertain": match_uncertain,
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
