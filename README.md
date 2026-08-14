# SSP Sniper 🎯

A command-line interface (CLI) application designed to intercept high-intent, high-ticket development clients on Reddit. It utilizes a Regex pre-filter to cut down noise and relies on an LLM (OpenAI) to qualify business leads based on strict budget and technical criteria. High-quality leads are then routed to a Discord Webhook for immediate team action.

## Prerequisites
- Python 3.9+
- A Reddit Developer App (for Client ID / Client Secret). Create one at `https://www.reddit.com/prefs/apps` (Select "script").
- An OpenAI API Key (`gpt-4o-mini` is used by default).

## Installation

1. Clone or download this project.
2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

## Usage

The CLI operates in two distinct modes: **Batch** and **Stream**.

### Batch Mode
Fetches the last N posts from your target subreddits. Useful for one-off scraping or catching up on missed posts.

```bash
# Fetch default subreddits (100 posts)
python ssp_sniper.py batch

# Specify custom subreddits and a custom limit
python ssp_sniper.py batch -s python,reactjs,SideProject -l 50
```

### Stream Mode
Listens to the subreddit feed in real-time. PRAW automatically handles Reddit's standard API rate limits. Perfect for running on a VPS or background daemon.

```bash
# Stream from default subreddits continuously
python ssp_sniper.py stream

# Stream from specific subreddits
python ssp_sniper.py stream --subreddits SaaS,startups,Entrepreneur
```

## How It Works
1. **Local Deduplication:** `leads.db` (SQLite) is created locally to track processed post IDs and prevent duplicate API processing and webhooks.
2. **Regex Filter:** Checks Title + Body for technical pain points or hiring signals.
3. **LLM Qualification:** Pings OpenAI with a strict system prompt to determine B2B legitimacy and budget.
4. **Handoff:** Prints a clean, formatted table in the terminal using `rich` and appends the lead data to `qualified_leads.csv`.
