from unittest.mock import MagicMock, patch

import pytest

from app.services.llm import summarize, process_unsummarized


# ---------------------------------------------------------------------------
# summarize() tests
# ---------------------------------------------------------------------------

def _mock_response(text: str) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


def test_summarize_returns_text():
    with patch("app.services.llm._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response("A great summary.")
        result = summarize("My Title", "Some long article content here.")

    assert result == "A great summary."


def test_summarize_truncates_long_content():
    long_content = "x" * 20_000
    with patch("app.services.llm._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response("Summary.")
        summarize("Title", long_content)

    call_args = mock_client.return_value.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert len(prompt) < 20_000


def test_summarize_includes_title_in_prompt():
    with patch("app.services.llm._get_client") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response("Summary.")
        summarize("My Article Title", "Content here.")

    call_args = mock_client.return_value.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "My Article Title" in prompt


def test_summarize_returns_none_for_empty_content():
    assert summarize("Title", "") is None
    assert summarize("Title", "   ") is None


def test_summarize_returns_none_for_none_content():
    assert summarize("Title", None) is None


# ---------------------------------------------------------------------------
# process_unsummarized() tests
# ---------------------------------------------------------------------------

def _make_article(id: int, content: str | None = "Article content") -> MagicMock:
    article = MagicMock()
    article.id = id
    article.title = f"Article {id}"
    article.content = content
    article.summary = None
    return article


def test_process_unsummarized_saves_summaries():
    articles = [_make_article(1), _make_article(2)]
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = articles

    with patch("app.services.llm.get_session", return_value=mock_session), \
         patch("app.services.llm.summarize", return_value="A summary.") as mock_summarize:
        count = process_unsummarized()

    assert count == 2
    assert articles[0].summary == "A summary."
    assert articles[1].summary == "A summary."
    mock_session.commit.assert_called_once()


def test_process_unsummarized_skips_when_summarize_returns_none():
    articles = [_make_article(1)]
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = articles

    with patch("app.services.llm.get_session", return_value=mock_session), \
         patch("app.services.llm.summarize", return_value=None):
        count = process_unsummarized()

    assert count == 0
    assert articles[0].summary is None
    mock_session.commit.assert_called_once()


def test_process_unsummarized_returns_zero_when_nothing_to_process():
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

    with patch("app.services.llm.get_session", return_value=mock_session), \
         patch("app.services.llm.summarize") as mock_summarize:
        count = process_unsummarized()

    assert count == 0
    mock_summarize.assert_not_called()
