from datetime import datetime, timezone

from app import database
from app.models import Article, Source
from app.scrapers import blog, youtube
from app.services import email
from app import digest


def run() -> None:
    database.create_tables()
    session = database.get_session()

    try:
        _scrape(session)
        digest.generate_digests(session)
        articles = digest.build_email_digest(session)

        if not articles:
            print("No new articles to send.")
            return

        html = digest.format_html(articles, datetime.now(timezone.utc))
        email.send_digest(
            subject=f"AI News Digest — {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            html_body=html,
        )
        digest.mark_sent(session, articles)
        print(f"Digest sent with {len(articles)} articles.")

    finally:
        session.close()


def _scrape(session) -> None:
    _save_blog_posts(session)
    _save_youtube_videos(session)


def _save_blog_posts(session) -> None:
    posts = blog.scrape()
    for post in posts:
        exists = session.query(Article).filter_by(url=post.url).first()
        if exists:
            continue

        source = _get_or_create_source(session, name=post.source, type="rss", url=post.url)
        session.add(
            Article(
                source_id=source.id,
                title=post.title,
                url=post.url,
                content=post.content,
                published_at=post.published_at,
            )
        )
    session.commit()


def _save_youtube_videos(session) -> None:
    videos = youtube.scrape()
    for video in videos:
        exists = session.query(Article).filter_by(url=video.url).first()
        if exists:
            continue

        source = _get_or_create_source(session, name=video.channel, type="youtube", url=video.url)
        session.add(
            Article(
                source_id=source.id,
                title=video.title,
                url=video.url,
                published_at=video.published_at,
            )
        )
    session.commit()


def _get_or_create_source(session, name: str, type: str, url: str) -> Source:
    source = session.query(Source).filter_by(name=name).first()
    if not source:
        source = Source(name=name, type=type, url=url)
        session.add(source)
        session.flush()
    return source
