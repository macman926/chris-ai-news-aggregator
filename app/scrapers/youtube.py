from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


YOUTUBE_CHANNELS: list[dict[str, str]] = [
    # {"name": "Channel Name", "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID"},
]


@dataclass
class VideoEntry:
    title: str
    url: str
    published_at: datetime | None
    channel: str


def scrape(hours: int = 24) -> list[VideoEntry]:
    entries: list[VideoEntry] = []
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600

    for channel in YOUTUBE_CHANNELS:
        feed = feedparser.parse(channel["feed_url"])
        for entry in feed.entries:
            published = entry.get("published_parsed")
            if published:
                pub_ts = datetime(*published[:6], tzinfo=timezone.utc).timestamp()
                if pub_ts < cutoff:
                    continue
                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            else:
                pub_dt = None

            entries.append(
                VideoEntry(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    published_at=pub_dt,
                    channel=channel["name"],
                )
            )

    return entries
