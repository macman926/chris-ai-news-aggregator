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
graph LR
    A[Sources<br/>YouTube<br/>RSS Feeds] --> B[Scrapers<br/>BaseScraper<br/>Registry Pattern]
    B --> C[(Database<br/>PostgreSQL)]
    C --> D[Processors<br/>Markdown<br/>Transcripts<br/>Digests]
    D --> C
    C --> E[Curator<br/>LLM Ranking]
    E --> F[Email<br/>Personalized Digest]
    F --> G[Delivery<br/>Gmail SMTP]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
    style D fill:#fff4e1
    style E fill:#f3e5f5
    style F fill:#f3e5f5
    style G fill:#ffe1f5
```

## How It Works

### Pipeline Flow

1. **Scraping** (`app/scrapers/`)
   - Runs all registered scrapers
   - Fetches articles/videos from configured sources
   - Saves raw content to database

2. **Processing** (`app/services/llm.py`)
   - Converts content to markdown
   - Fetches video transcripts
   - Generates summaries using LLM

3. **Digest Generation** (`app/digest.py`)
   - Ranks articles by relevance to user profile
   - Uses LLM to score and curate content

4. **Email Generation** (`app/services/email.py`)
   - Creates personalized email digest
   - Selects top N articles
   - Generates introduction and formats content
   - Marks digests as sent to prevent duplicates

5. **Delivery** (`app/services/email.py`)
   - Sends HTML email via Gmail SMTP

### Daily Pipeline

The `app/scheduler.py` orchestrates all steps:
- Ensures database tables exist
- Scrapes all sources
- Processes content (markdown, transcripts)
- Creates digests
- Sends email

## Project Structure

```
ai-news-aggregator/
├── app/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models (Source, Article)
│   ├── database.py        # Database connection and session management
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── youtube.py     # YouTube RSS feed scraper
│   │   └── blog.py        # Blog post scraper (OpenAI, Anthropic)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py         # LLM summarization service
│   │   └── email.py       # Email sending service
│   ├── digest.py          # Daily digest generation logic
│   └── scheduler.py       # Main scheduler/entry point
├── docker/
│   ├── Dockerfile         # Minimal Python app container
│   └── docker-compose.yml # Optional: PostgreSQL + app setup
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── main.py                # CLI entry point
└── pyproject.toml         # Project configuration
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

Then register it in `app/scheduler.py`:

```python
from .scrapers.my_scraper import MyScraper

SCRAPER_REGISTRY = [
    # ... existing scrapers
    MyScraper(),
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
   pip install -r requirements.txt
   ```

3. Configure environment variables (copy `.env.example` to `.env`):
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
   python -m app.database
   ```

5. Configure YouTube channels in `app/scrapers/youtube.py`

### Running

**Full pipeline:**
```bash
python main.py
```

**Individual steps:**
```bash
# Scraping
python -m app.scrapers.youtube
python -m app.scrapers.blog

# Processing & summarization
python -m app.services.llm

# Digest generation
python -m app.digest

# Email
python -m app.services.email
```

## Deployment

### Render.com

The project is configured for deployment on Render.com:

1. **Database**: PostgreSQL service (auto-configured)
2. **Cron Job**: Scheduled daily execution via `render.yaml`
3. **Environment**: Automatically detected as PRODUCTION when `DATABASE_URL` contains "render.com" (no manual setting needed)

See `RENDER_SETUP.md` for detailed deployment instructions.

### Docker

Build and run using the files in `docker/`:
```bash
docker build -f docker/Dockerfile -t ai-news-aggregator .
docker run --env-file .env ai-news-aggregator
```

Or use Docker Compose (includes PostgreSQL):
```bash
docker-compose -f docker/docker-compose.yml up
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

## License

MIT