# AI News Aggregator

An intelligent news aggregation system that scrapes AI-related content from multiple sources (YouTube channels, RSS feeds), processes them with LLM-powered summarization, curates personalized digests based on user preferences, and delivers daily email summaries.

## Overview

This project aggregates AI news from multiple sources:
- **YouTube Channels**: Scrapes videos and transcripts from configured channels
- **RSS Feeds**: Monitors OpenAI and Anthropic blog posts
- **Processing**: Converts content to markdown, generates summaries, and creates digests
- **Curation**: Ranks articles by relevance to user profile using LLM
- **Delivery**: Sends personalized daily email digests

## Architecture

```mermaid
flowchart TD
    subgraph SRC ["📡  Sources"]
        YT["📺 YouTube Channels"]
        RSS["📰 RSS Feeds · OpenAI & Anthropic"]
    end

    subgraph SCRAPE ["🔍  Scrapers"]
        SC["Scraper Registry · BaseScraper"]
    end

    DB[("🗄️  PostgreSQL")]

    subgraph PROC ["⚙️  Processing"]
        MD["📝 Markdown Converter"]
        TR["🎬 Transcript Fetcher"]
        DG["✨ Digest Generator"]
    end

    subgraph CUR ["🧠  Curation"]
        CA["Curator Agent · LLM Relevance Ranking"]
    end

    subgraph DELV ["📬  Delivery"]
        EA["Email Agent · Personalized Digest"]
        SMTP["Gmail SMTP"]
    end

    YT --> SC
    RSS --> SC
    SC --> DB
    DB --> MD & TR
    MD & TR --> DG
    DG --> DB
    DB --> CA
    CA --> EA --> SMTP

    classDef source fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f,rx:6
    classDef scraper fill:#fef9c3,stroke:#ca8a04,color:#713f12,rx:6
    classDef db fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:3px
    classDef process fill:#fef3c7,stroke:#f59e0b,color:#78350f,rx:6
    classDef curate fill:#f3e8ff,stroke:#a855f7,color:#4a1772,rx:6
    classDef deliver fill:#fce7f3,stroke:#ec4899,color:#831843,rx:6

    class YT,RSS source
    class SC scraper
    class DB db
    class MD,TR,DG process
    class CA curate
    class EA,SMTP deliver
```

## How It Works

### Pipeline Flow

1. **Scraping** (`app/runner.py`)
   - Runs all registered scrapers
   - Fetches articles/videos from configured sources
   - Saves raw content to database

2. **Processing** (`app/services/process_*.py`)
   - **Anthropic**: Converts HTML articles to markdown
   - **YouTube**: Fetches video transcripts
   - **Digests**: Generates summaries using LLM

3. **Curation** (`app/services/process_curator.py`)
   - Ranks digests by relevance to user profile
   - Uses LLM to score and rank articles

4. **Email Generation** (`app/services/process_email.py`)
   - Creates personalized email digest
   - Selects top N articles
   - Generates introduction and formats content
   - Marks digests as sent to prevent duplicates

5. **Delivery** (`app/services/email.py`)
   - Sends HTML email via Gmail SMTP

### Daily Pipeline

The `run_daily_pipeline()` function orchestrates all steps:
- Ensures database tables exist
- Scrapes all sources
- Processes content (markdown, transcripts)
- Creates digests
- Sends email

## Project Structure

```
app/
├── agent/              # LLM agents for processing
│   ├── base.py        # Base agent class
│   ├── curator_agent.py   # Article ranking
│   ├── digest_agent.py    # Summary generation
│   └── email_agent.py     # Email content generation
├── config.py          # Configuration (YouTube channels)
├── database/          # Database layer
│   ├── models.py      # SQLAlchemy models
│   ├── repository.py # Data access layer
│   └── connection.py  # DB connection & environment
├── profiles/          # User profile configuration
│   └── user_profile.py
├── scrapers/          # Content scrapers
│   ├── base.py        # Base scraper for RSS feeds
│   ├── anthropic.py   # Anthropic RSS scraper
│   ├── openai.py      # OpenAI RSS scraper
│   └── youtube.py     # YouTube channel scraper
├── services/          # Processing services
│   ├── base.py        # Base process service
│   ├── process_anthropic.py
│   ├── process_youtube.py
│   ├── process_digest.py
│   ├── process_curator.py
│   ├── process_email.py
│   └── email.py       # Email sending
├── daily_runner.py    # Main pipeline orchestrator
└── runner.py          # Scraper registry & execution
```

## Adding New Scrapers

### RSS Feed Scraper (Easiest)

Create a new file in `app/scrapers/`:

```python
from typing import List
from .base import BaseScraper, Article

class MyArticle(Article):
    pass

class MyScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return ["https://example.com/feed.xml"]

    def get_articles(self, hours: int = 24) -> List[MyArticle]:
        return [MyArticle(**a.model_dump()) for a in super().get_articles(hours)]
```

Then register it in `app/runner.py`:

```python
from .scrapers.my_scraper import MyScraper

def _save_my_articles(scraper, repo, hours):
    return _save_rss_articles(scraper, repo, hours, repo.bulk_create_my_articles)

SCRAPER_REGISTRY = [
    # ... existing scrapers
    ("my_source", MyScraper(), _save_my_articles),
]
```

### Custom Scraper

For non-RSS sources, inherit from the base pattern:

```python
class CustomScraper:
    def get_articles(self, hours: int = 24) -> List[Article]:
        # Your custom scraping logic
        pass
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL database
- OpenAI API key
- Gmail app password (for email sending)
- Webshare proxy credentials (optional, for YouTube transcript fetching)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables (copy `app/example.env` to `.env`):
   ```bash
   OPENAI_API_KEY=your_key
   MY_EMAIL=your_email@gmail.com
   APP_PASSWORD=your_gmail_app_password
   DATABASE_URL=postgresql://user:pass@host:port/db
   ENVIRONMENT=LOCAL  # Optional: auto-detected from DATABASE_URL if contains "render.com"
   
   # Optional: Webshare Proxy (for YouTube transcript fetching)
   # Get credentials from https://www.webshare.io/
   WEBSHARE_USERNAME=your_username
   WEBSHARE_PASSWORD=your_password
   ```
   
   **Note**: Webshare proxy is optional. If not provided, YouTube transcript fetching will work without a proxy but may be rate-limited.

4. Initialize database:
   ```bash
   uv run python -m app.database.create_tables
   ```
   
   Or check database connection:
   ```bash
   uv run python -m app.database.check_connection
   ```

5. Configure YouTube channels in `app/config.py`

6. Update user profile in `app/profiles/user_profile.py`

### Running

**Full pipeline:**
```bash
uv run main.py
```

**Individual steps:**
```bash
# Scraping
uv run python -m app.runner

# Processing
uv run python -m app.services.process_anthropic
uv run python -m app.services.process_youtube
uv run python -m app.services.process_digest

# Curation
uv run python -m app.services.process_curator

# Email
uv run python -m app.services.process_email
```

## Deployment

### Render.com

The project is configured for deployment on Render.com:

1. **Database**: PostgreSQL service (auto-configured)
2. **Cron Job**: Scheduled daily execution via `render.yaml`
3. **Environment**: Automatically detected as PRODUCTION when `DATABASE_URL` contains "render.com" (no manual setting needed)

See `RENDER_SETUP.md` for detailed deployment instructions.

### Docker

Build and run:
```bash
docker build -t ai-news-aggregator .
docker run --env-file .env ai-news-aggregator
```

## Key Features

- **Modular Architecture**: Base classes make it easy to extend
- **Scraper Registry**: Add new sources with minimal code
- **LLM-Powered**: Uses OpenAI for summarization and curation
- **Personalized**: User profile-based ranking
- **Duplicate Prevention**: Tracks sent digests
- **Environment Aware**: Supports LOCAL and PRODUCTION environments

## Technology Stack

- **Python 3.12+**: Core language
- **PostgreSQL**: Database
- **SQLAlchemy**: ORM
- **Pydantic**: Data validation
- **OpenAI API**: LLM processing
- **feedparser**: RSS parsing
- **youtube-transcript-api**: Video transcripts
- **UV**: Package management

## License

MIT