"""
Unit tests for cookie handling and sameSite normalization.
"""

import pytest

from src.api.auth_routes import convert_editthiscookie_to_playwright, normalize_same_site
from src.core.auth_manager import sanitize_cookies


class TestSameSiteNormalization:
    """Tests for sameSite attribute normalization."""

    def test_normalize_same_site_lowercase(self):
        """Test normalization of lowercase sameSite values."""
        assert normalize_same_site("lax") == "Lax"
        assert normalize_same_site("strict") == "Strict"
        assert normalize_same_site("none") == "None"

    def test_normalize_same_site_proper_case(self):
        """Test that proper case values are preserved."""
        assert normalize_same_site("Lax") == "Lax"
        assert normalize_same_site("Strict") == "Strict"
        assert normalize_same_site("None") == "None"

    def test_normalize_same_site_no_restriction(self):
        """Test normalization of 'no_restriction' (EditThisCookie format)."""
        assert normalize_same_site("no_restriction") == "None"
        assert normalize_same_site("unspecified") == "None"

    def test_normalize_same_site_empty_or_invalid(self):
        """Test that empty or invalid values default to 'Lax'."""
        assert normalize_same_site("") == "Lax"
        assert normalize_same_site(None) == "Lax"
        assert normalize_same_site("invalid_value") == "Lax"
        assert normalize_same_site(123) == "Lax"


class TestConvertEditThisCookieToPlaywright:
    """Tests for EditThisCookie to Playwright cookie conversion."""

    def test_convert_cookies_with_lowercase_same_site(self):
        """Test conversion with lowercase sameSite values."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".example.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "lax",
            }
        ]
        result = convert_editthiscookie_to_playwright(cookies)
        assert len(result) == 1
        assert result[0]["sameSite"] == "Lax"

    def test_convert_cookies_with_no_restriction(self):
        """Test conversion with 'no_restriction' sameSite value."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".example.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "no_restriction",
            }
        ]
        result = convert_editthiscookie_to_playwright(cookies)
        assert result[0]["sameSite"] == "None"

    def test_convert_cookies_with_expiration_date(self):
        """Test conversion of expirationDate to expires."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".example.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax",
                "expirationDate": 1735689600.0,
            }
        ]
        result = convert_editthiscookie_to_playwright(cookies)
        assert result[0]["expires"] == 1735689600

    def test_convert_cookies_missing_same_site(self):
        """Test conversion when sameSite is missing (should default to Lax)."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".example.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }
        ]
        result = convert_editthiscookie_to_playwright(cookies)
        assert result[0]["sameSite"] == "Lax"


class TestSanitizeCookies:
    """Tests for cookie sanitization in auth_manager."""

    def test_sanitize_cookies_with_invalid_same_site(self):
        """Test sanitization of cookies with invalid sameSite values."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".linkedin.com",
                "sameSite": "invalid",
            }
        ]
        result = sanitize_cookies(cookies)
        assert result[0]["sameSite"] == "Lax"

    def test_sanitize_cookies_adds_missing_same_site(self):
        """Test that missing sameSite attribute is added."""
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".linkedin.com",
            }
        ]
        result = sanitize_cookies(cookies)
        assert "sameSite" in result[0]
        assert result[0]["sameSite"] == "Lax"

    def test_sanitize_cookies_preserves_other_fields(self):
        """Test that sanitization preserves all other cookie fields."""
        cookies = [
            {
                "name": "li_at",
                "value": "test_token",
                "domain": ".linkedin.com",
                "path": "/",
                "expires": 9999999999,
                "httpOnly": True,
                "secure": True,
                "sameSite": "none",
            }
        ]
        result = sanitize_cookies(cookies)
        assert result[0]["name"] == "li_at"
        assert result[0]["value"] == "test_token"
        assert result[0]["domain"] == ".linkedin.com"
        assert result[0]["path"] == "/"
        assert result[0]["expires"] == 9999999999
        assert result[0]["httpOnly"] is True
        assert result[0]["secure"] is True
        assert result[0]["sameSite"] == "None"  # Normalized
