# 🎯 HR Candidate Finder

AI-Powered LinkedIn Talent Discovery — Find the perfect candidates in minutes, not days.

## Features

| Feature | Description |
|---------|-------------|
| **Smart Discovery** | Google dorking via Serper.dev finds LinkedIn profiles matching your exact requirements |
| **Profile Enrichment** | Apify scrapers pull full profile data (skills, experience, education, contacts) |
| **AI Analysis** | Gemini 2.0 Flash evaluates fit score, role match, green/red flags |
| **Contact Extraction** | Auto-extracts emails, phones, GitHub, websites from profiles |
| **Tier Scoring** | Scores candidates A/B/C/D based on fit + contactability + recommendation |
| **Deep Search Loop** | Multi-round orchestrated search until target count is reached |
| **Dashboard** | Plotly visualizations: tier donut, role match, experience chart, quality map |
| **CSV Export** | Download all candidates or just Tier A+B with 24 fields |

## Setup

### 1. Install Dependencies

```bash
cd hr_candidate_finder
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the example secrets file and add your keys:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your actual keys.

### API Keys Required

| Service | Key Name | Purpose | Cost |
|---------|----------|---------|------|
| [Serper.dev](https://serper.dev) | `SERPER_API_KEY` | Google Search (LinkedIn dorking) | Free: 2,500 queries |
| [Google AI Studio](https://aistudio.google.com) | `GOOGLE_API_KEY` | Gemini 2.0 Flash (AI analysis) | Free: 15 req/min |
| [Apify](https://apify.com) | `APIFY_KEY_1` | LinkedIn scraping (paid account) | $29/month |
| [Apify](https://apify.com) | `APIFY_KEY_2` | LinkedIn scraping (free account) | $5 free credit |
| [Apify](https://apify.com) | `APIFY_KEY_3` | LinkedIn scraping (free account) | $5 free credit |
| [Apify](https://apify.com) | `APIFY_KEY_4` | LinkedIn scraping (free account) | $5 free credit |

> **Cost Optimization**: Free Apify keys (2→3→4) are used first. Paid key (1) is last resort.

### 3. Run the App

```bash
streamlit run app.py
```

## Cost Per Search Session

For a typical search of ~25 candidates:

| API | Usage | Cost |
|-----|-------|------|
| Serper.dev | ~15-30 queries | ~$0.03 |
| Apify | ~60-100 profiles | ~$0.15-$0.25 |
| Gemini | ~25-50 calls | Free |
| **Total** | | **~$0.20-$0.30** |

## How It Works

```
1. DISCOVER  — Serper.dev Google dorking for LinkedIn profiles
2. DEDUP     — Skip already-sourced candidates (CSV upload)
3. ENRICH    — Apify scrapes full profile data
4. FILTER    — Completeness, keyword, location, connections, blacklist
5. ANALYZE   — Gemini AI evaluates fit score + hire recommendation
6. CONTACTS  — Extract emails, phones, GitHub, websites
7. TIER      — Score A/B/C/D based on fit + contactability
8. LOOP      — Repeat rounds until target count reached
9. DASHBOARD — Visualize with Plotly charts + export CSV
```

## File Structure

```
hr_candidate_finder/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
└── .streamlit/
    ├── config.toml                 # Streamlit theme config
    └── secrets.toml.example        # API key template
```

## Safety Limits

| Limit | Value | Purpose |
|-------|-------|---------|
| MAX_SERPER_QUERIES | 50 | Protect free tier |
| MAX_APIFY_SCRAPES | 300 | Control costs |
| MAX_GEMINI_CALLS | 300 | Stay within free tier |
| MAX_ROUNDS | 15 | Prevent infinite loops |

## Tech Stack

- **Frontend**: Streamlit
- **Search**: Serper.dev (Google Search API)
- **Scraping**: Apify (LinkedIn profile scrapers)
- **AI**: Google Gemini 2.0 Flash
- **Charts**: Plotly
- **Data**: Pandas

---

Built with ❤️ for HR professionals by eQOURSE
