import pytest

from app.auth import AuthError, _extract_bearer_token


def test_extract_bearer_token_ok() -> None:
    assert _extract_bearer_token("Bearer abc123") == "abc123"


@pytest.mark.parametrize("value", [None, "", "abc", "Token abc", "Bearer   "])
def test_extract_bearer_token_invalid(value: str | None) -> None:
    with pytest.raises(AuthError):
        _extract_bearer_token(value)
