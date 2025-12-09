from __future__ import annotations

from urllib.parse import urlparse

import pytest
from hypothesis import given
from hypothesis import strategies as st

from msftoolbox.azure.auth.scopes import authority_from_url, spo_scope_from_url

# Strategy: absolute http/https URLs with host
abs_urls = st.builds(
    lambda scheme, host, path: f"{scheme}://{host}{path}",
    scheme=st.sampled_from(["http", "https"]),
    host=st.from_regex(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}", fullmatch=True
    ),
    path=st.from_regex(r"(?:/[A-Za-z0-9._~!$&'()*+,;=:@%-]*)*", fullmatch=True),
)


@given(abs_urls)
def test_authority_from_url__round_trip(url: str) -> None:
    """Returns scheme://host for valid absolute URLs."""
    auth = authority_from_url(url)
    parsed = urlparse(url)
    assert auth == f"{parsed.scheme}://{parsed.netloc}"
    # authority is itself absolute without path/query
    assert "://" in auth and parsed.netloc in auth


@given(abs_urls)
def test_spo_scope_from_url__appends_default(url: str) -> None:
    """Appends '/.default' to the authority of the input URL."""
    assert spo_scope_from_url(url).endswith("/.default")
    assert spo_scope_from_url(url).startswith(authority_from_url(url))


@pytest.mark.parametrize(
    "bad",
    ["", "foo", "/relative", "://", "http:///only-path", "https://"],
)
def test_authority_from_url__invalid_inputs_raise(bad: str) -> None:
    """Relative or malformed URLs must raise ValueError."""
    with pytest.raises(ValueError, match="must be an absolute URL"):
        authority_from_url(bad)
