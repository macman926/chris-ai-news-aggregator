from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Article
from app.services import llm

USER_PROFILE = """
I am an AI practitioner interested in:
- Large language model research and capabilities
- AI safety and alignment
- Practical AI engineering and tooling
- Industry trends and product launches
"""


def generate_digests(session: Session) -> None:
    unsummarized = (
        session.query(Article)
        .filter(Article.summary.is_(None), Article.content.isnot(None))
        .all()
    )

    for article in unsummarized:
        article.summary = llm.summarize(article.content, article.title)

    session.commit()


def build_email_digest(session: Session, top_n: int = 10) -> list[Article]:
    articles = (
        session.query(Article)
        .filter(Article.summary.isnot(None), Article.digest_sent.is_(False))
        .order_by(Article.published_at.desc())
        .all()
    )

    article_dicts = [
        {"title": a.title, "summary": a.summary, "url": a.url, "id": a.id}
        for a in articles
    ]
    ranked = llm.rank_articles(article_dicts, USER_PROFILE)

    top_ids = {r["id"] for r in ranked[:top_n]}
    return [a for a in articles if a.id in top_ids]


def mark_sent(session: Session, articles: list[Article]) -> None:
    for article in articles:
        article.digest_sent = True
    session.commit()


def format_html(articles: list[Article], date: datetime) -> str:
    items = "".join(
        f"""
        <div style="margin-bottom:24px;">
            <h2 style="margin:0 0 4px;"><a href="{a.url}">{a.title}</a></h2>
            <p style="margin:0;color:#555;">{a.summary}</p>
        </div>
        """
        for a in articles
    )

    return f"""
    <html><body style="font-family:sans-serif;max-width:700px;margin:auto;padding:24px;">
        <h1>AI News Digest — {date.strftime("%B %d, %Y")}</h1>
        {items}
    </body></html>
    """
