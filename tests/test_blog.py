from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.scrapers.blog import _fetch_content, _parse_anthropic_date, _scrape_anthropic_news


# ---------------------------------------------------------------------------
# Content fetching tests
# ---------------------------------------------------------------------------

def test_fetch_content_success():
    html = "<html><body><main><p>Hello world</p></main></body></html>"
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    with patch("app.scrapers.blog.httpx.get", return_value=mock_response):
        result = _fetch_content("https://example.com/article")

    assert result is not None
    assert "Hello world" in result


def test_fetch_content_http_error():
    with patch("app.scrapers.blog.httpx.get", side_effect=Exception("connection error")):
        assert _fetch_content("https://example.com/article") is None


def test_fetch_content_strips_nav_and_footer():
    html = """
    <html><body>
        <nav>Nav links</nav>
        <main><p>Real content</p></main>
        <footer>Footer text</footer>
    </body></html>
    """
    mock_response = MagicMock()
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()

    with patch("app.scrapers.blog.httpx.get", return_value=mock_response):
        result = _fetch_content("https://example.com/article")

    assert "Real content" in result
    assert "Nav links" not in result
    assert "Footer text" not in result


# ---------------------------------------------------------------------------
# Anthropic date parser tests
# ---------------------------------------------------------------------------

def test_parse_anthropic_date_valid():
    dt = _parse_anthropic_date("Jun 12, 2026")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 12
    assert dt.tzinfo == timezone.utc


def test_parse_anthropic_date_invalid():
    assert _parse_anthropic_date("not a date") is None
    assert _parse_anthropic_date("") is None


# ---------------------------------------------------------------------------
# Anthropic news scraper tests
# ---------------------------------------------------------------------------

ANTHROPIC_HTML = """
<html><body>
  <a href="/news/claude-update">
    <h2>Claude Gets Smarter</h2>
    <time>Jun 11, 2026</time>
  </a>
  <a href="/news/old-post">
    <h4>Old News</h4>
    <time>Jan 1, 2020</time>
  </a>
  <a href="/about">No time tag here</a>
</body></html>
"""


def test_scrape_anthropic_news_filters_by_time():
    mock_response = MagicMock()
    mock_response.text = ANTHROPIC_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("app.scrapers.blog.httpx.get", return_value=mock_response):
        results = _scrape_anthropic_news(hours=24 * 365)  # wide window to catch recent entries

    urls = [r["url"] for r in results]
    assert any("claude-update" in u for u in urls)
    assert not any("old-post" in u for u in urls)  # 2020 is outside any window
    assert not any("/about" in u for u in urls)   # no <time> tag


def test_scrape_anthropic_news_builds_full_url():
    mock_response = MagicMock()
    mock_response.text = ANTHROPIC_HTML
    mock_response.raise_for_status = MagicMock()

    with patch("app.scrapers.blog.httpx.get", return_value=mock_response):
        results = _scrape_anthropic_news(hours=24 * 365)

    assert all(r["url"].startswith("https://www.anthropic.com") for r in results)


def test_scrape_anthropic_news_http_error_returns_empty():
    with patch("app.scrapers.blog.httpx.get", side_effect=Exception("timeout")):
        assert _scrape_anthropic_news(hours=24) == []


# ---------------------------------------------------------------------------
# scrape() tests
# ---------------------------------------------------------------------------

TEST_FEED = {"name": "Test Blog", "url": "https://example.com/rss.xml"}


def _make_entry(hours_ago: float) -> dict:
    ts = datetime.now(timezone.utc).timestamp() - hours_ago * 3600
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return {
        "published_parsed": dt.timetuple(),
        "link": "https://example.com/posts/test-post",
        "title": "Test Post Title",
    }


def _mock_session(existing_article=None) -> MagicMock:
    from app.models import Article, Source

    fake_source = MagicMock()
    fake_source.id = 1
    session = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model is Source:
            q.filter_by.return_value.first.return_value = fake_source
        elif model is Article:
            q.filter_by.return_value.first.return_value = existing_article
        return q

    session.query.side_effect = query_side_effect
    return session


def test_scrape_saves_new_post():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=1)]
    mock_session = _mock_session(existing_article=None)

    with patch("app.scrapers.blog.RSS_FEEDS", [TEST_FEED]), \
         patch("app.scrapers.blog.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.blog.get_session", return_value=mock_session), \
         patch("app.scrapers.blog._fetch_content", return_value="article text"), \
         patch("app.scrapers.blog._scrape_anthropic_news", return_value=[]):
        from app.scrapers import blog
        blog.scrape()

    assert mock_session.add.call_count == 1
    assert mock_session.commit.call_count == 2  # once for RSS, once for Anthropic


def test_scrape_skips_old_posts():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=25)]
    mock_session = _mock_session(existing_article=None)

    with patch("app.scrapers.blog.RSS_FEEDS", [TEST_FEED]), \
         patch("app.scrapers.blog.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.blog.get_session", return_value=mock_session), \
         patch("app.scrapers.blog._fetch_content", return_value=None), \
         patch("app.scrapers.blog._scrape_anthropic_news", return_value=[]):
        from app.scrapers import blog
        blog.scrape()

    assert mock_session.add.call_count == 0


def test_scrape_skips_duplicates():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=1)]
    mock_session = _mock_session(existing_article=MagicMock())

    with patch("app.scrapers.blog.RSS_FEEDS", [TEST_FEED]), \
         patch("app.scrapers.blog.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.blog.get_session", return_value=mock_session), \
         patch("app.scrapers.blog._fetch_content", return_value="text"), \
         patch("app.scrapers.blog._scrape_anthropic_news", return_value=[]):
        from app.scrapers import blog
        blog.scrape()

    assert mock_session.add.call_count == 0


# ---------------------------------------------------------------------------
# Integration tests — hit real endpoints (requires network)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_openai_rss_feed_live():
    import feedparser
    feed = feedparser.parse("https://openai.com/news/rss.xml")
    assert len(feed.entries) > 0
    for entry in feed.entries:
        assert entry.get("title")
        assert entry.get("link")


@pytest.mark.integration
def test_anthropic_news_page_live():
    results = _scrape_anthropic_news(hours=24 * 365)
    assert len(results) > 0
    for r in results:
        assert r["title"]
        assert r["url"].startswith("https://www.anthropic.com/news/")
        assert isinstance(r["published_at"], datetime)
