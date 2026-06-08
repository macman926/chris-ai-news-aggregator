import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def summarize(content: str, title: str) -> str:
    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Summarize the following article in 3-5 concise sentences. "
                    f"Focus on the key points and why it matters for AI practitioners.\n\n"
                    f"Title: {title}\n\n{content}"
                ),
            }
        ],
    )
    return message.content[0].text


def rank_articles(articles: list[dict], user_profile: str) -> list[dict]:
    if not articles:
        return []

    client = _get_client()
    article_list = "\n".join(
        f"{i + 1}. {a['title']}: {a.get('summary', '')[:200]}"
        for i, a in enumerate(articles)
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Given this user profile:\n{user_profile}\n\n"
                    f"Rank these articles by relevance (most relevant first). "
                    f"Return only a comma-separated list of numbers.\n\n{article_list}"
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    try:
        order = [int(x.strip()) - 1 for x in raw.split(",")]
        return [articles[i] for i in order if 0 <= i < len(articles)]
    except (ValueError, IndexError):
        return articles
