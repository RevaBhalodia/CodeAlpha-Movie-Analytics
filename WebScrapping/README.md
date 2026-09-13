# Movie Analytics — CodeAlpha Data Analytics Internship

One connected project covering all four internship tasks, built around a single theme:
**movie data + audience sentiment.**

## Why one theme for all four tasks

Doing four unrelated mini-scripts is what most interns submit. Building one pipeline —
scrape → clean/explore → visualize → analyze sentiment — reads like real analyst work,
and it's a much stronger portfolio piece and LinkedIn video.

## Project structure

```
CodeAlpha_MovieAnalytics/
├── data/
│   ├── movies_raw.csv          # Task 1 output
│   ├── movies_clean.csv        # Task 2 output
│   └── reviews_labeled.csv     # Task 4 output
├── scrape_movies.py            # Task 1
├── eda_movies.ipynb            # Task 2 (built next)
├── visualize_movies.ipynb      # Task 3 (built next)
├── sentiment_analysis.ipynb    # Task 4 (built next)
├── requirements.txt
└── README.md
```

## Task 1 — Web Scraping ✅ (built)

`scrape_movies.py`:
- Scrapes the Wikipedia "List of highest-grossing films" table with `requests` + `BeautifulSoup`.
- Enriches every title with genre, IMDb rating, runtime, director, language, country,
  and box office via the free [OMDb API](https://www.omdbapi.com/apikey.aspx).
- Saves progress checkpoints so a long run never loses data.

**To run:**
```bash
pip install -r requirements.txt
export OMDB_API_KEY="your_free_key_here"   # get one at omdbapi.com/apikey.aspx
python scrape_movies.py
```

Output: `data/movies_raw.csv`

## Task 2 — EDA (next)

Questions we'll answer:
- Which genres dominate the highest-grossing list, and has that changed by decade?
- Does IMDb rating actually correlate with box office success?
- What's missing/messy in the data (OMDb misses, inconsistent runtime formats, currency
  formatting in gross figures) and how do we clean it?

## Task 3 — Data Visualization (next)

Turning the EDA findings into a small set of polished charts: genre trends over time,
rating vs. gross scatter, top directors by average rating, etc.

## Task 4 — Sentiment Analysis (next)

Using the well-known IMDb 50K movie review dataset to classify reviews as positive/negative,
then connecting it back to Task 1–3's data: do audience sentiment patterns line up with
critic ratings for the same films?

## Internship submission checklist (per CodeAlpha instructions)

- [ ] Post internship status on LinkedIn, tag @CodeAlpha
- [ ] Push source code to a GitHub repo named `CodeAlpha_MovieAnalytics` (or per-task repos
      if that's what your batch requires — check your WhatsApp group instructions)
- [ ] Record a short video walking through the project, post on LinkedIn with the repo link
- [ ] Submit via the official submission form
- [ ] Complete at least 2–3 tasks minimum (we're doing all 4)
