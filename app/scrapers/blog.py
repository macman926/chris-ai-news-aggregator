from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


RSS_FEEDS: list[dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/news/rss.xml"},
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/rss.xml"},
]


@dataclass
class BlogPost:
    title: str
    url: str
    published_at: datetime | None
    source: str
    content: str


def scrape(hours: int = 24) -> list[BlogPost]:
    posts: list[BlogPost] = []
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600

    for feed_config in RSS_FEEDS:
        feed = feedparser.parse(feed_config["url"])
        for entry in feed.entries:
            published = entry.get("published_parsed")
            if published:
                pub_ts = datetime(*published[:6], tzinfo=timezone.utc).timestamp()
                if pub_ts < cutoff:
                    continue
                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            else:
                pub_dt = None

            content = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")

            posts.append(
                BlogPost(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    published_at=pub_dt,
                    source=feed_config["name"],
                    content=content,
                )
            )

    return posts
