"""
Device Profiles — coherent browser identity bundles for anti-detection.

Each profile bundles UA, locale, timezone, viewport, platform, and geo hint
into a consistent "persona" that passes cross-signal validation. Anti-bot
systems check that all signals tell the same story (e.g. a German locale
should come with a European timezone and DE geo proxy).

Usage:
    profile = DeviceProfile.random()
    profile = DeviceProfile.for_geo("US")
    profile = DeviceProfile.for_browser("chrome")
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DeviceProfile:
    """A coherent browser identity — all fields are mutually consistent."""

    user_agent: str
    browser: str          # "chrome" | "firefox" | "safari"
    browser_version: str  # e.g. "131"
    platform: str         # "Windows" | "macOS" | "Linux"
    locale: str           # e.g. "en-US"
    accept_language: str  # e.g. "en-US,en;q=0.9"
    timezone: str         # IANA timezone
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    screen: dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    color_depth: int = 24
    pixel_ratio: float = 1.0
    hardware_concurrency: int = 8
    geo_hint: Optional[str] = None  # ISO country code for proxy selection
    impersonate_target: str = "chrome131"  # curl_cffi impersonate string

    @classmethod
    def random(cls, geo: Optional[str] = None) -> DeviceProfile:
        """Select a random profile, optionally filtered by geo region."""
        pool = DEVICE_PROFILES
        if geo:
            geo_upper = geo.upper()
            geo_pool = [p for p in pool if p.geo_hint == geo_upper]
            if geo_pool:
                pool = geo_pool
        return random.choice(pool)

    @classmethod
    def for_geo(cls, geo: str) -> DeviceProfile:
        """Get a profile matching a geographic region."""
        return cls.random(geo=geo)

    @classmethod
    def for_browser(cls, browser: str) -> DeviceProfile:
        """Get a profile for a specific browser type."""
        pool = [p for p in DEVICE_PROFILES if p.browser == browser.lower()]
        return random.choice(pool) if pool else cls.random()


# =============================================================================
# Profile Database — real-world device combinations
#
# Each entry is a tested, coherent combination. Never randomize individual
# fields — always pick a complete profile.
# =============================================================================

_CHROME_131_WIN_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/New_York",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_US_2 = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Chicago",
    viewport={"width": 1366, "height": 768},
    screen={"width": 1366, "height": 768},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=4,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_US_3 = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Los_Angeles",
    viewport={"width": 1536, "height": 864},
    screen={"width": 1536, "height": 864},
    color_depth=24,
    pixel_ratio=1.25,
    hardware_concurrency=12,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_MAC_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="macOS",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/New_York",
    viewport={"width": 1440, "height": 900},
    screen={"width": 2560, "height": 1600},
    color_depth=30,
    pixel_ratio=2.0,
    hardware_concurrency=10,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_MAC_US_2 = DeviceProfile(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="macOS",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Los_Angeles",
    viewport={"width": 1680, "height": 1050},
    screen={"width": 3360, "height": 2100},
    color_depth=30,
    pixel_ratio=2.0,
    hardware_concurrency=8,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_UK = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-GB",
    accept_language="en-GB,en;q=0.9",
    timezone="Europe/London",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="GB",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_DE = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="de-DE",
    accept_language="de-DE,de;q=0.9,en;q=0.8",
    timezone="Europe/Berlin",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="DE",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_FR = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="fr-FR",
    accept_language="fr-FR,fr;q=0.9,en;q=0.8",
    timezone="Europe/Paris",
    viewport={"width": 1366, "height": 768},
    screen={"width": 1366, "height": 768},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=4,
    geo_hint="FR",
    impersonate_target="chrome131",
)

_FIREFOX_132_WIN_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    browser="firefox",
    browser_version="132",
    platform="Windows",
    locale="en-US",
    accept_language="en-US,en;q=0.5",
    timezone="America/New_York",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="US",
    impersonate_target="chrome131",  # curl_cffi doesn't support firefox impersonation
)

_FIREFOX_132_MAC_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    browser="firefox",
    browser_version="132",
    platform="macOS",
    locale="en-US",
    accept_language="en-US,en;q=0.5",
    timezone="America/Chicago",
    viewport={"width": 1440, "height": 900},
    screen={"width": 2560, "height": 1600},
    color_depth=30,
    pixel_ratio=2.0,
    hardware_concurrency=10,
    geo_hint="US",
    impersonate_target="chrome131",
)

_SAFARI_17_MAC_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    browser="safari",
    browser_version="17.6",
    platform="macOS",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/New_York",
    viewport={"width": 1440, "height": 900},
    screen={"width": 2560, "height": 1600},
    color_depth=30,
    pixel_ratio=2.0,
    hardware_concurrency=10,
    geo_hint="US",
    impersonate_target="safari17_2_ios",
)

_CHROME_131_LINUX_US = DeviceProfile(
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Linux",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/New_York",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=16,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_CA = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-CA",
    accept_language="en-CA,en;q=0.9,fr-CA;q=0.8",
    timezone="America/Toronto",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="CA",
    impersonate_target="chrome131",
)

_CHROME_131_WIN_AU = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-AU",
    accept_language="en-AU,en;q=0.9",
    timezone="Australia/Sydney",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="AU",
    impersonate_target="chrome131",
)

# Master pool of all profiles
DEVICE_PROFILES: list[DeviceProfile] = [
    _CHROME_131_WIN_US,
    _CHROME_131_WIN_US_2,
    _CHROME_131_WIN_US_3,
    _CHROME_131_MAC_US,
    _CHROME_131_MAC_US_2,
    _CHROME_131_WIN_UK,
    _CHROME_131_WIN_DE,
    _CHROME_131_WIN_FR,
    _FIREFOX_132_WIN_US,
    _FIREFOX_132_MAC_US,
    _SAFARI_17_MAC_US,
    _CHROME_131_LINUX_US,
    _CHROME_131_WIN_CA,
    _CHROME_131_WIN_AU,
]


def get_headers_for_profile(profile: DeviceProfile) -> dict[str, str]:
    """Build browser-realistic HTTP headers from a device profile.

    Header order matches real Chrome/Firefox output — this matters
    for header-order fingerprinting.
    """
    if profile.browser == "chrome":
        return {
            "sec-ch-ua": f'"Chromium";v="{profile.browser_version}", "Google Chrome";v="{profile.browser_version}", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{profile.platform}"',
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": profile.accept_language,
        }
    elif profile.browser == "firefox":
        return {
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": profile.accept_language,
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    else:  # safari
        return {
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": profile.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }


def get_referer_for_url(url: str) -> Optional[str]:
    """Generate a plausible referrer for a URL (Google search or homepage)."""
    from urllib.parse import urlparse, quote_plus
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")

    # 70% chance of Google referrer, 30% chance of direct (no referrer)
    if random.random() < 0.7:
        # Simulate coming from a Google search
        search_term = domain.split(".")[0]
        return f"https://www.google.com/search?q={quote_plus(search_term)}"
    return None
