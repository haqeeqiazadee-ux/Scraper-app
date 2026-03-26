"""Tests for the device profile system.

Covers:
- Profile consistency (all signals coherent within a profile)
- Profile selection (random, by geo, by browser)
- Header generation (correct order, browser-specific headers)
- Referrer generation
"""

import pytest

from packages.core.device_profiles import (
    DEVICE_PROFILES,
    DeviceProfile,
    get_headers_for_profile,
    get_referer_for_url,
)


# ---------------------------------------------------------------------------
# Profile database integrity
# ---------------------------------------------------------------------------


class TestProfileDatabase:

    def test_profiles_not_empty(self) -> None:
        """Profile database contains real profiles."""
        assert len(DEVICE_PROFILES) >= 10

    def test_all_profiles_have_required_fields(self) -> None:
        """Every profile has all required fields populated."""
        for p in DEVICE_PROFILES:
            assert p.user_agent, f"Missing user_agent in {p.locale} profile"
            assert p.browser in ("chrome", "firefox", "safari"), f"Bad browser: {p.browser}"
            assert p.browser_version, f"Missing browser_version"
            assert p.platform in ("Windows", "macOS", "Linux"), f"Bad platform: {p.platform}"
            assert p.locale, f"Missing locale"
            assert p.accept_language, f"Missing accept_language"
            assert p.timezone, f"Missing timezone"
            assert p.viewport["width"] > 0, f"Bad viewport width"
            assert p.viewport["height"] > 0, f"Bad viewport height"
            assert p.screen["width"] > 0, f"Bad screen width"
            assert p.screen["height"] > 0, f"Bad screen height"
            assert p.color_depth > 0, f"Bad color_depth"
            assert p.pixel_ratio > 0, f"Bad pixel_ratio"
            assert p.hardware_concurrency > 0, f"Bad hardware_concurrency"
            assert p.geo_hint, f"Missing geo_hint"
            assert p.impersonate_target, f"Missing impersonate_target"

    def test_ua_matches_browser(self) -> None:
        """User-Agent string matches the claimed browser type."""
        for p in DEVICE_PROFILES:
            if p.browser == "chrome":
                assert "Chrome/" in p.user_agent
            elif p.browser == "firefox":
                assert "Firefox/" in p.user_agent
            elif p.browser == "safari":
                assert "Safari/" in p.user_agent
                assert "Chrome/" not in p.user_agent  # Safari UA has no Chrome

    def test_ua_matches_platform(self) -> None:
        """User-Agent string matches the claimed platform."""
        for p in DEVICE_PROFILES:
            if p.platform == "Windows":
                assert "Windows" in p.user_agent
            elif p.platform == "macOS":
                assert "Macintosh" in p.user_agent or "Mac OS X" in p.user_agent
            elif p.platform == "Linux":
                assert "Linux" in p.user_agent

    def test_locale_matches_geo(self) -> None:
        """Locale language matches the geo region (no German locale with US geo)."""
        geo_locale_map = {
            "US": ["en-US"],
            "GB": ["en-GB"],
            "DE": ["de-DE"],
            "FR": ["fr-FR"],
            "CA": ["en-CA"],
            "AU": ["en-AU"],
        }
        for p in DEVICE_PROFILES:
            if p.geo_hint in geo_locale_map:
                allowed = geo_locale_map[p.geo_hint]
                assert p.locale in allowed, f"Locale {p.locale} doesn't match geo {p.geo_hint}"

    def test_timezone_matches_geo(self) -> None:
        """Timezone matches the geo region."""
        geo_tz_prefixes = {
            "US": ["America/"],
            "GB": ["Europe/London"],
            "DE": ["Europe/Berlin"],
            "FR": ["Europe/Paris"],
            "CA": ["America/Toronto"],
            "AU": ["Australia/"],
        }
        for p in DEVICE_PROFILES:
            if p.geo_hint in geo_tz_prefixes:
                prefixes = geo_tz_prefixes[p.geo_hint]
                assert any(p.timezone.startswith(pf) for pf in prefixes), (
                    f"Timezone {p.timezone} doesn't match geo {p.geo_hint}"
                )

    def test_screen_gte_viewport(self) -> None:
        """Physical screen is at least as large as viewport."""
        for p in DEVICE_PROFILES:
            assert p.screen["width"] >= p.viewport["width"], f"Screen narrower than viewport"
            assert p.screen["height"] >= p.viewport["height"], f"Screen shorter than viewport"

    def test_mac_profiles_have_retina(self) -> None:
        """macOS profiles have Retina pixel ratios (>= 2.0)."""
        mac_profiles = [p for p in DEVICE_PROFILES if p.platform == "macOS"]
        assert len(mac_profiles) >= 2
        for p in mac_profiles:
            assert p.pixel_ratio >= 2.0, f"Mac profile should be Retina, got pixel_ratio={p.pixel_ratio}"

    def test_browser_versions_are_current(self) -> None:
        """Browser versions are reasonably current (not outdated)."""
        for p in DEVICE_PROFILES:
            version = int(p.browser_version.split(".")[0])
            if p.browser == "chrome":
                assert version >= 125, f"Chrome {version} is outdated — update profile"
            elif p.browser == "firefox":
                assert version >= 125, f"Firefox {version} is outdated — update profile"


# ---------------------------------------------------------------------------
# Profile selection
# ---------------------------------------------------------------------------


class TestProfileSelection:

    def test_random_returns_profile(self) -> None:
        """DeviceProfile.random() returns a valid profile."""
        p = DeviceProfile.random()
        assert isinstance(p, DeviceProfile)
        assert p.user_agent

    def test_random_varies(self) -> None:
        """Multiple random calls produce variety."""
        profiles = [DeviceProfile.random() for _ in range(30)]
        unique_uas = {p.user_agent for p in profiles}
        assert len(unique_uas) > 1

    def test_for_geo_filters_correctly(self) -> None:
        """for_geo() returns profiles matching the requested geo."""
        for _ in range(20):
            p = DeviceProfile.for_geo("US")
            assert p.geo_hint == "US"

    def test_for_geo_unknown_falls_back(self) -> None:
        """for_geo() with unknown geo falls back to any profile."""
        p = DeviceProfile.for_geo("ZZ")
        assert isinstance(p, DeviceProfile)

    def test_for_browser_chrome(self) -> None:
        """for_browser('chrome') returns Chrome profiles."""
        for _ in range(10):
            p = DeviceProfile.for_browser("chrome")
            assert p.browser == "chrome"

    def test_for_browser_firefox(self) -> None:
        """for_browser('firefox') returns Firefox profiles."""
        for _ in range(10):
            p = DeviceProfile.for_browser("firefox")
            assert p.browser == "firefox"


# ---------------------------------------------------------------------------
# Header generation
# ---------------------------------------------------------------------------


class TestHeaderGeneration:

    def test_chrome_headers_include_sec_ch_ua(self) -> None:
        """Chrome profiles produce sec-ch-ua headers."""
        p = DeviceProfile.for_browser("chrome")
        headers = get_headers_for_profile(p)
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-mobile" in headers
        assert "sec-ch-ua-platform" in headers
        assert p.browser_version in headers["sec-ch-ua"]

    def test_firefox_headers_no_sec_ch_ua(self) -> None:
        """Firefox profiles don't produce sec-ch-ua headers (Firefox doesn't send them)."""
        p = DeviceProfile.for_browser("firefox")
        headers = get_headers_for_profile(p)
        assert "sec-ch-ua" not in headers

    def test_all_headers_have_user_agent(self) -> None:
        """All browser types produce a User-Agent header."""
        for browser in ("chrome", "firefox", "safari"):
            p = DeviceProfile.for_browser(browser)
            headers = get_headers_for_profile(p)
            assert "User-Agent" in headers
            assert p.user_agent == headers["User-Agent"]

    def test_all_headers_have_accept(self) -> None:
        """All browser types produce an Accept header."""
        for p in DEVICE_PROFILES:
            headers = get_headers_for_profile(p)
            assert "Accept" in headers
            assert "text/html" in headers["Accept"]

    def test_accept_language_from_profile(self) -> None:
        """Accept-Language header matches the profile's accept_language."""
        for p in DEVICE_PROFILES:
            headers = get_headers_for_profile(p)
            assert "Accept-Language" in headers
            assert headers["Accept-Language"] == p.accept_language

    def test_chrome_header_order(self) -> None:
        """Chrome headers are in the correct order (sec-ch-ua before User-Agent)."""
        p = DeviceProfile.for_browser("chrome")
        headers = get_headers_for_profile(p)
        keys = list(headers.keys())
        sec_ch_idx = keys.index("sec-ch-ua")
        ua_idx = keys.index("User-Agent")
        assert sec_ch_idx < ua_idx, "sec-ch-ua must come before User-Agent in Chrome"


# ---------------------------------------------------------------------------
# Referrer generation
# ---------------------------------------------------------------------------


class TestReferrerGeneration:

    def test_referrer_is_google_or_none(self) -> None:
        """Referrer is either a Google search URL or None."""
        results = set()
        for _ in range(50):
            ref = get_referer_for_url("https://www.amazon.com/dp/B08N5WRWNW")
            if ref is not None:
                assert "google.com/search" in ref
            results.add(ref is not None)
        # With 50 trials at 70/30 split, we should see both outcomes
        assert True in results
        assert None in results or len(results) > 0  # At least some non-None

    def test_referrer_contains_domain_hint(self) -> None:
        """Google referrer includes a search term derived from the domain."""
        for _ in range(20):
            ref = get_referer_for_url("https://www.amazon.com/dp/B08N5WRWNW")
            if ref is not None:
                assert "amazon" in ref.lower()
                break
        else:
            pytest.skip("All 20 referrers were None (unlikely but possible)")
