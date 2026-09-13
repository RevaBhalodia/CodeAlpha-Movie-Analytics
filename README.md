# CodeAlpha Movie Analytics

Data Analytics Internship project — CodeAlpha. All four internship tasks built as one
connected pipeline around a single theme: **movie data + audience sentiment.**

## Why one project instead of four separate scripts

Task 1 scrapes and builds the dataset, Task 2 explores it, Task 3 visualizes the findings,
and Task 4 layers in sentiment analysis on real movie reviews — connecting back to the
same movies where possible. One story end to end, rather than four disconnected exercises.

## Project structure

```
CodeAlpha-Movie-Analytics/
└── WebScrapping/
    ├── data/
    │   └── movies_raw.csv       # Task 1 output — 250 highest-grossing films,
    │                             # enriched with genre, IMDb rating, runtime,
    │                             # director, box office, awards, etc.
    ├── scrape_movies.py          # Task 1
    ├── requirements.txt
    └── README.md
```
(EDA, visualization, and sentiment analysis notebooks are being added as the project
progresses — see status below.)

## Task 1 — Web Scraping ✅

`scrape_movies.py` scrapes the Wikipedia "List of highest-grossing films" table with
`requests` + `BeautifulSoup`, then enriches every title with genre, IMDb rating, runtime,
director, language, country, box office, and awards via the free
[OMDb API](https://www.omdbapi.com/apikey.aspx).

**To run:**
```bash
cd WebScrapping
pip install -r requirements.txt
python scrape_movies.py
```
Output: `data/movies_raw.csv`

## Task 2 — Exploratory Data Analysis 🔜

Planned questions: Which genres dominate the highest-grossing list, and has that shifted
by decade? Does IMDb rating actually correlate with box office success? What's messy or
missing in the scraped/enriched data, and how should it be cleaned?

## Task 3 — Data Visualization 🔜

Turning the EDA findings into a small set of clear charts: genre trends over time,
rating vs. gross, top directors by average rating, etc.

## Task 4 — Sentiment Analysis 🔜

Classifying real movie reviews (IMDb 50K review dataset) as positive/negative, then
checking whether audience sentiment patterns line up with critic ratings for the same
films from Task 1's data.

## Tech stack

Python · pandas · BeautifulSoup · requests · OMDb API · matplotlib/seaborn · NLTK/VADER

## Internship info

Built as part of the CodeAlpha Data Analytics internship (codealpha.tech).
