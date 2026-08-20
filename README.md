# SSP Hunter

**Engineering Opportunity Intelligence CLI**

SSP Hunter is a local-first engineering opportunity intelligence system. It discovers, analyzes, scores, qualifies, and organizes high-intent prospects experiencing specific engineering problems.

Unlike generic scrapers, it uses a multi-stage deterministic signal pipeline combined with Groq LLM (LLaMA-3.3-70b) to ensure only highly qualified B2B leads make it to your workflow.

## Supported Niches
1. **AI → Production (`ai-production`)**: Prospects who built prototypes using AI tools (Cursor, Lovable, Bolt) and are struggling with scaling, production deployment, and reliability.
2. **Codebase Takeover (`takeover`)**: Founders and businesses whose previous developer left or agency disappeared, leaving them with a legacy codebase that needs rescuing.

## Architecture

* **CLI:** `Typer` & `Rich`
* **Configuration:** Pydantic
* **Database:** SQLite & `SQLModel`
* **Data Sources:** 
  * Reddit (via open JSON endpoints)
  * Hacker News (via Algolia)
  * Web Discovery (via DuckDuckGo)
* **LLM:** Groq (`llama-3.1-70b-versatile` fallback) via OpenAI SDK

## Installation

```bash
# Ensure you have Python 3.11+
python -m venv .venv
# Activate virtual environment
.\.venv\Scripts\Activate.ps1   # Windows
# or source .venv/bin/activate # Linux/Mac

# Install the package locally
pip install -e .
```

## Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update your `.env` with real credentials:
```env
GROQ_API_KEY=gsk_your_real_key_here
REDDIT_USER_AGENT="ssp_hunter:v1.0 (by /u/YOUR_ACTUAL_REDDIT_USERNAME)"
```

*Note: If your REDDIT_USER_AGENT is generic, Reddit will block your requests (429/403).*

## Usage

### 1. Check Configuration
```bash
ssp config
```

### 2. Discover Leads
Run a discovery hunt for the AI -> Production niche:
```bash
ssp hunt ai-production
```
Run a hunt for the Codebase Takeover niche, showing verbose rejection reasons:
```bash
ssp hunt takeover --verbose
```

### 3. View Saved Leads
View a table of all leads stored in the local SQLite database:
```bash
ssp leads
ssp leads --niche ai-production
ssp leads --min-score 70
```

## Advanced Customization
* **New Niches:** Add a new class inheriting from `BaseNiche` in `src/ssp/niches/`. Define the regex signals and scoring matrix.
* **Database Location:** Stored by default in `data/ssp.db`. Configurable via `DATABASE_URL` in `.env`.
