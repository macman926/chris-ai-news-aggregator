from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import feedparser
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

_yt_api = YouTubeTranscriptApi()

from app.database import create_tables, get_session
from app.models import Article, Source

# Add channels here: find a channel's ID by going to their YouTube page,
# clicking "More", then "Share channel" -> "Copy channel ID".
# RSS feed format: https://www.youtube.com/feeds/videos.xml?channel_id=<ID>
CHANNELS: list[dict[str, str]] = [
    # {"name": "Andrej Karpathy", "channel_id": "UCbXgNpp0jedKWcQiULLbDTA"},
]


def _rss_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def _video_id(url: str) -> str | None:
    qs = parse_qs(urlparse(url).query)
    ids = qs.get("v")
    return ids[0] if ids else None


def _fetch_transcript(video_id: str) -> str | None:
    try:
        transcript = _yt_api.fetch(video_id)
        return " ".join(snippet.text for snippet in transcript)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None


def _get_or_create_source(session, channel: dict) -> Source:
    source = session.query(Source).filter_by(name=channel["name"]).first()
    if not source:
        source = Source(
            name=channel["name"],
            type="youtube",
            url=_rss_url(channel["channel_id"]),
        )
        session.add(source)
        session.flush()
    return source


def scrape(hours: int = 24) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    session = get_session()

    try:
        for channel in CHANNELS:
            feed = feedparser.parse(_rss_url(channel["channel_id"]))
            source = _get_or_create_source(session, channel)
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

                video_id = _video_id(url)
                transcript = _fetch_transcript(video_id) if video_id else None

                session.add(
                    Article(
                        source_id=source.id,
                        title=entry.get("title", ""),
                        url=url,
                        content=transcript,
                        published_at=pub_dt,
                    )
                )
                new_count += 1

            session.commit()
            print(f"{channel['name']}: {new_count} new video(s) saved.")

    finally:
        session.close()


if __name__ == "__main__":
    create_tables()
    scrape()
