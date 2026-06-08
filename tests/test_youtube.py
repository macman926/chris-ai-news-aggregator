from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.scrapers.youtube import _fetch_transcript, _rss_url, _video_id


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------

def test_video_id_standard_url():
    assert _video_id("https://www.youtube.com/watch?v=abc123") == "abc123"


def test_video_id_invalid_url():
    assert _video_id("https://example.com") is None


def test_rss_url_format():
    assert _rss_url("UCabc123") == "https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123"


# ---------------------------------------------------------------------------
# Transcript fetch tests
# ---------------------------------------------------------------------------

def _make_snippets(*texts: str) -> list[MagicMock]:
    snippets = []
    for t in texts:
        s = MagicMock()
        s.text = t
        snippets.append(s)
    return snippets


def test_fetch_transcript_success():
    with patch("app.scrapers.youtube._yt_api.fetch", return_value=_make_snippets("Hello", "world")):
        assert _fetch_transcript("abc123") == "Hello world"


def test_fetch_transcript_disabled():
    with patch("app.scrapers.youtube._yt_api.fetch", side_effect=Exception("TranscriptsDisabled")):
        assert _fetch_transcript("abc123") is None


def test_fetch_transcript_not_found():
    with patch("app.scrapers.youtube._yt_api.fetch", side_effect=Exception("NoTranscriptFound")):
        assert _fetch_transcript("abc123") is None


def test_fetch_transcript_unexpected_error():
    with patch("app.scrapers.youtube._yt_api.fetch", side_effect=Exception("something unexpected")):
        assert _fetch_transcript("abc123") is None


# ---------------------------------------------------------------------------
# scrape() tests
# ---------------------------------------------------------------------------

TEST_CHANNEL = {"name": "Test Channel", "channel_id": "UCtest123"}


def _make_entry(hours_ago: float) -> dict:
    ts = datetime.now(timezone.utc).timestamp() - hours_ago * 3600
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return {
        "published_parsed": dt.timetuple(),
        "link": "https://www.youtube.com/watch?v=testvideo1",
        "title": "Test Video Title",
    }


def _mock_session(existing_article=None) -> MagicMock:
    """Return a mock session. existing_source is always pre-existing to isolate Article adds."""
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


def test_scrape_saves_new_video():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=1)]
    mock_session = _mock_session(existing_article=None)

    with patch("app.scrapers.youtube.CHANNELS", [TEST_CHANNEL]), \
         patch("app.scrapers.youtube.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.youtube.get_session", return_value=mock_session), \
         patch("app.scrapers.youtube._fetch_transcript", return_value="transcript text"):
        from app.scrapers import youtube
        youtube.scrape()

    assert mock_session.add.call_count == 1, "Expected one Article to be saved"
    mock_session.commit.assert_called_once()


def test_scrape_skips_old_videos():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=25)]  # older than 24h window
    mock_session = _mock_session(existing_article=None)

    with patch("app.scrapers.youtube.CHANNELS", [TEST_CHANNEL]), \
         patch("app.scrapers.youtube.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.youtube.get_session", return_value=mock_session), \
         patch("app.scrapers.youtube._fetch_transcript", return_value=None):
        from app.scrapers import youtube
        youtube.scrape()

    assert mock_session.add.call_count == 0, "Old video should not be saved"


def test_scrape_skips_duplicates():
    mock_feed = MagicMock()
    mock_feed.entries = [_make_entry(hours_ago=1)]
    existing = MagicMock()  # Article already in DB
    mock_session = _mock_session(existing_article=existing)

    with patch("app.scrapers.youtube.CHANNELS", [TEST_CHANNEL]), \
         patch("app.scrapers.youtube.feedparser.parse", return_value=mock_feed), \
         patch("app.scrapers.youtube.get_session", return_value=mock_session), \
         patch("app.scrapers.youtube._fetch_transcript", return_value="text"):
        from app.scrapers import youtube
        youtube.scrape()

    assert mock_session.add.call_count == 0, "Duplicate URL should not be saved again"


# ---------------------------------------------------------------------------
# Integration test — hits real YouTube RSS (requires network)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_rss_feed_live():
    import feedparser

    # Anthropic's YouTube channel
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCTwEMeIxV1PfCFR0gDuY01A"
    feed = feedparser.parse(url)

    assert len(feed.entries) > 0, "Expected at least one video in the Anthropic feed"
    for entry in feed.entries:
        assert entry.get("title"), f"Entry missing title: {entry}"
        assert entry.get("link"), f"Entry missing link: {entry}"
