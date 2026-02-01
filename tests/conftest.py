"""Pytest fixtures for integration tests."""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from urllib.error import HTTPError


@pytest.fixture
def mock_github_available():
    """Patch urlopen so GitHub API returns 404 (available) for given usernames."""
    def _make(available: set[str] | None = None):
        available = available or set()

        def fake_urlopen(req, timeout=10):
            url = req.full_url if hasattr(req, 'full_url') else req.get_full_url()
            username = url.rstrip('/').split('/users/')[-1]

            if username in available:
                raise HTTPError(url, 404, "Not Found", {}, None)
            return MagicMock(__enter__=lambda self: MagicMock(status=200), __exit__=lambda *a: None)

        return patch('ghunt.checker.urlopen', side_effect=fake_urlopen)

    return _make


@pytest.fixture
def mock_github_by_check():
    """Patch is_username_available with a custom checker function."""
    def _make(check_fn):
        return patch(
            'ghunt.checker.is_username_available',
            side_effect=check_fn,
        )

    return _make


@pytest.fixture
def no_sleep():
    """Disable time.sleep for fast tests."""
    with patch('ghunt.checker.time.sleep'):
        yield


@pytest.fixture
def no_token(monkeypatch):
    """Clear GITHUB_TOKEN env."""
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)


@contextmanager
def capture_stdout():
    """Capture print output."""
    from io import StringIO
    old = sys.stdout
    buf = StringIO()
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old
