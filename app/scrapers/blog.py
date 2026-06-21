from datetime import datetime, timezone

import feedparser
import html2text
import httpx
from bs4 import BeautifulSoup

from app.database import create_tables, get_session
from app.models import Article, Source

ANTHROPIC_NEWS_URL = "https://www.anthropic.com/news"

RSS_FEEDS: list[dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/news/rss.xml"},
    # Add more RSS feeds here as needed:
    # {"name": "My Source", "url": "https://example.com/feed.xml"},
]

_converter = html2text.HTML2Text()
_converter.ignore_links = True
_converter.ignore_images = True

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ai-news-aggregator/1.0)"}


def _fetch_content(url: str) -> str | None:
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True, headers=_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            return None

        return _converter.handle(str(main)).strip() or None
    except Exception:
        return None


def _parse_anthropic_date(text: str) -> datetime | None:
    try:
        return datetime.strptime(text.strip(), "%b %d, %Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _scrape_anthropic_news(hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    try:
        response = httpx.get(ANTHROPIC_NEWS_URL, timeout=15, headers=_HEADERS)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "lxml")
    articles = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href.startswith("/news/"):
            continue

        time_tag = a.find("time")
        if not time_tag:
            continue

        pub_dt = _parse_anthropic_date(time_tag.get_text())
        if not pub_dt or pub_dt.timestamp() < cutoff:
            continue

        title_tag = a.find(["h2", "h3", "h4"])
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            continue

        articles.append({
            "title": title,
            "url": f"https://www.anthropic.com{href}",
            "published_at": pub_dt,
        })

    return articles


def _get_or_create_source(session, name: str, url: str, type: str = "rss") -> Source:
    source = session.query(Source).filter_by(name=name).first()
    if not source:
        source = Source(name=name, type=type, url=url)
        session.add(source)
        session.flush()
    return source


def scrape(hours: int = 24) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    session = get_session()

    try:
        # RSS feeds
        for feed_config in RSS_FEEDS:
            feed = feedparser.parse(feed_config["url"])
            source = _get_or_create_source(session, feed_config["name"], feed_config["url"])
            new_count = 0

            for entry in feed.entries:
                published_parsed = entry.get("published_parsed")
                if not published_parsed:
                    continue

                pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                if pub_dt.timestamp() < cutoff:
                    continue

                url = entry.get("link", "")
                if session.query(Article).filter_by(url=url).first():
                    continue

                session.add(Article(
                    source_id=source.id,
                    title=entry.get("title", ""),
                    url=url,
                    content=_fetch_content(url),
                    published_at=pub_dt,
                ))
                new_count += 1

            session.commit()
            print(f"{feed_config['name']}: {new_count} new post(s) saved.")

        # Anthropic custom scraper
        anthropic_source = _get_or_create_source(
            session, "Anthropic Blog", ANTHROPIC_NEWS_URL, type="web"
        )
        anthropic_new = 0

        for article in _scrape_anthropic_news(hours):
            if session.query(Article).filter_by(url=article["url"]).first():
                continue

            session.add(Article(
                source_id=anthropic_source.id,
                title=article["title"],
                url=article["url"],
                content=_fetch_content(article["url"]),
                published_at=article["published_at"],
            ))
            anthropic_new += 1

        session.commit()
        print(f"Anthropic Blog: {anthropic_new} new post(s) saved.")

    finally:
        session.close()


if __name__ == "__main__":
    create_tables()
    scrape()
