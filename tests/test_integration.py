"""Full integration tests for ghunt."""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ghunt import (
    find_available_from_llm,
    get_token,
    is_username_available,
)
from ghunt.checker import check_with_rate_limit
from ghunt.llm_generator import _extract_usernames, _is_valid_username


# --- Checker ---


@pytest.mark.integration
def test_checker_requires_token():
    """is_username_available and check_with_rate_limit raise when token not set (no anonymous usage)."""
    with pytest.raises(ValueError, match="token required"):
        is_username_available("x", token=None)
    with pytest.raises(ValueError, match="token required"):
        check_with_rate_limit("x", token=None)


@pytest.mark.integration
def test_checker_available_vs_taken(mock_github_available):
    """is_username_available returns True for 404, False for 200 (token required)."""
    with mock_github_available({'xyz123'}):
        assert is_username_available('xyz123', token="fake") is True
        assert is_username_available('octocat', token="fake") is False


@pytest.mark.integration
def test_checker_rate_limit_raises(mock_github_available):
    """403 from GitHub raises RuntimeError."""
    from urllib.error import HTTPError

    def raise_403(req, timeout=10):
        raise HTTPError("", 403, "Forbidden", {}, None)

    with patch('ghunt.checker.urlopen', side_effect=raise_403):
        with pytest.raises(RuntimeError, match="rate limit"):
            is_username_available("x", token="fake")


# --- LLM generator ---


@pytest.mark.integration
def test_llm_extract_usernames():
    """_extract_usernames parses various LLM output formats."""
    text = "abc\nxyz\n\ndev-1, foo2\n\nbar"
    result = _extract_usernames(text, min_length=1, max_length=6)
    assert 'abc' in result
    assert 'xyz' in result
    assert 'dev-1' in result
    assert 'foo2' in result
    assert 'bar' in result


@pytest.mark.integration
def test_llm_extract_respects_max_length():
    """_extract_usernames rejects names outside min_length–max_length."""
    text = "ab toolongname xy"
    result = _extract_usernames(text, min_length=1, max_length=4)
    assert 'ab' in result
    assert 'xy' in result
    assert 'toolongname' not in result


@pytest.mark.integration
def test_llm_is_valid_username():
    """_is_valid_username validates GitHub username rules and length range."""
    assert _is_valid_username("a", min_length=1, max_length=4) is True
    assert _is_valid_username("abc", min_length=1, max_length=4) is True
    assert _is_valid_username("dev-1", min_length=1, max_length=5) is True
    assert _is_valid_username("a-b-c", min_length=1, max_length=5) is True
    assert _is_valid_username("") is False
    assert _is_valid_username("ab", min_length=1, max_length=1) is False
    assert _is_valid_username("a-b", min_length=1, max_length=4) is True
    assert _is_valid_username("-ab") is False
    assert _is_valid_username("ab-") is False
    # Default min_length=4, max_length=4
    assert _is_valid_username("abcd") is True
    assert _is_valid_username("abc", min_length=4, max_length=4) is False


@pytest.mark.integration
def test_llm_find_available_integration(mock_github_available, no_sleep, no_token, tmp_path):
    """LLM mode: mock Ollama response via injected client, real availability check."""
    fake_response = MagicMock()
    fake_response.message.content = "dev\nxyz\nabc\nfoo"
    fake_client = MagicMock()
    fake_client.chat.return_value = fake_response
    exclude_file = str(tmp_path / "checked.txt")

    with mock_github_available({'xyz'}):
        with patch('sys.stdout', new_callable=StringIO):
            result = find_available_from_llm(
                prompt="developer",
                min_length=1,
                max_length=4,
                limit=3,
                token="fake",
                exclude_file=exclude_file,
                client=fake_client,
            )

    assert 'xyz' in result
    assert len(result) <= 3
    assert fake_client.chat.call_count >= 1
    assert tmp_path.joinpath("checked.txt").read_text().strip()


# --- CLI ---


@pytest.mark.integration
def test_cli_runs_with_mocked_ollama(mock_github_available, no_sleep, no_token, capsys, tmp_path):
    """CLI runs and prints results when Ollama is mocked."""
    fake_response = MagicMock()
    fake_response.message.content = "dev\nxyz"
    fake_client = MagicMock()
    fake_client.chat.return_value = fake_response

    def with_client(*a, **kw):
        kw['client'] = fake_client
        return find_available_from_llm(*a, **kw)

    with mock_github_available({'xyz'}):
        with patch('sys.argv', ['ghunt', '-p', 'dev', '-n', '1', '-t', 'fake', '--exclude-file', str(tmp_path / 'x.txt')]):
            with patch('main.find_available_from_llm', with_client):
                from main import main
                main()

    captured = capsys.readouterr()
    assert "xyz" in captured.out or "available" in captured.out.lower()


@pytest.mark.integration
def test_cli_help(capsys):
    """CLI --help works."""
    with pytest.raises(SystemExit):
        with patch('sys.argv', ['ghunt', '--help']):
            from main import main
            main()
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower() or "ghunt" in captured.out


@pytest.mark.integration
def test_cli_requires_token(no_token, capsys):
    """CLI exits with error when no token."""
    with patch('sys.argv', ['ghunt', '-p', 'x', '-n', '1']):
        with pytest.raises(SystemExit) as exc_info:
            from main import main
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "token" in captured.out.lower()


# --- Checker (real GitHub; uses GITHUB_TOKEN or token.txt) ---


def _token_for_real_check() -> str | None:
    """Token from env or default token.txt (project root)."""
    token = get_token()
    if token:
        return token
    path = Path(__file__).resolve().parent.parent / "token.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip() or None
    return None


@pytest.mark.integration
def test_real_github_check():
    """Verify is_username_available against real GitHub; uses GITHUB_TOKEN or token.txt."""
    token = _token_for_real_check()
    if not token:
        pytest.fail("GITHUB_TOKEN or token.txt required for real API check")
    assert is_username_available("octocat", token=token) is False
    assert is_username_available("xyznonexistent12345abc", token=token) is True


# --- get_token ---


@pytest.mark.integration
def test_get_token_from_env(monkeypatch):
    """get_token reads GITHUB_TOKEN from environment."""
    monkeypatch.setenv('GITHUB_TOKEN', 'secret123')
    assert get_token() == 'secret123'
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    assert get_token() is None
