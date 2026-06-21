import os

import anthropic

from app.database import get_session
from app.models import Article

MODEL = "claude-haiku-4-5-20251001"

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def summarize(title: str, content: str) -> str | None:
    if not content or not content.strip():
        return None

    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarize the following article in 3-4 sentences. "
                    "Focus on the key points and why it matters for AI practitioners. "
                    "Be concise and direct.\n\n"
                    f"Title: {title}\n\n"
                    f"{content[:8000]}"  # cap to avoid token limits on long transcripts
                ),
            }
        ],
    )
    return message.content[0].text.strip()


def process_unsummarized(batch_size: int = 50) -> int:
    session = get_session()
    try:
        articles = (
            session.query(Article)
            .filter(Article.summary.is_(None), Article.content.isnot(None))
            .limit(batch_size)
            .all()
        )

        count = 0
        for article in articles:
            result = summarize(article.title, article.content)
            if result:
                article.summary = result
                count += 1

        session.commit()
        print(f"Summarized {count} article(s).")
        return count
    finally:
        session.close()


if __name__ == "__main__":
    process_unsummarized()
