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

# --- Sprint 5: Mobile, tablet, and additional desktop profiles ---------------

_CHROME_131_ANDROID_SAMSUNG_S24 = DeviceProfile(
    user_agent="Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Linux armv81",
    locale="ko-KR",
    accept_language="ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    timezone="Asia/Seoul",
    viewport={"width": 412, "height": 915},
    screen={"width": 412, "height": 915},
    color_depth=24,
    pixel_ratio=3.0,
    hardware_concurrency=8,
    geo_hint="KR",
    impersonate_target="chrome131",
)

_CHROME_131_ANDROID_PIXEL_8 = DeviceProfile(
    user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Linux armv81",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Los_Angeles",
    viewport={"width": 412, "height": 915},
    screen={"width": 412, "height": 915},
    color_depth=24,
    pixel_ratio=2.625,
    hardware_concurrency=8,
    geo_hint="US",
    impersonate_target="chrome131",
)

_CHROME_131_ANDROID_ONEPLUS_12 = DeviceProfile(
    user_agent="Mozilla/5.0 (Linux; Android 14; CPH2583) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Linux armv81",
    locale="en-IN",
    accept_language="en-IN,en;q=0.9,hi;q=0.8",
    timezone="Asia/Kolkata",
    viewport={"width": 412, "height": 915},
    screen={"width": 412, "height": 915},
    color_depth=24,
    pixel_ratio=3.0,
    hardware_concurrency=8,
    geo_hint="IN",
    impersonate_target="chrome131",
)

_CHROME_131_IOS_IPAD = DeviceProfile(
    user_agent="Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/131.0.6778.73 Mobile/15E148 Safari/604.1",
    browser="chrome",
    browser_version="131",
    platform="iPad",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/New_York",
    viewport={"width": 1024, "height": 1366},
    screen={"width": 1024, "height": 1366},
    color_depth=24,
    pixel_ratio=2.0,
    hardware_concurrency=6,
    geo_hint="US",
    impersonate_target="chrome131",
)

_SAFARI_17_IOS_IPHONE15 = DeviceProfile(
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    browser="safari",
    browser_version="17.6",
    platform="iPhone",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Los_Angeles",
    viewport={"width": 390, "height": 844},
    screen={"width": 390, "height": 844},
    color_depth=24,
    pixel_ratio=3.0,
    hardware_concurrency=6,
    geo_hint="US",
    impersonate_target="safari17_2_ios",
)

_SAFARI_17_IOS_IPHONE14 = DeviceProfile(
    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    browser="safari",
    browser_version="17.6",
    platform="iPhone",
    locale="en-GB",
    accept_language="en-GB,en;q=0.9",
    timezone="Europe/London",
    viewport={"width": 390, "height": 844},
    screen={"width": 390, "height": 844},
    color_depth=24,
    pixel_ratio=3.0,
    hardware_concurrency=6,
    geo_hint="GB",
    impersonate_target="safari17_2_ios",
)

_FIREFOX_132_LINUX_UBUNTU = DeviceProfile(
    user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    browser="firefox",
    browser_version="132",
    platform="Linux",
    locale="en-US",
    accept_language="en-US,en;q=0.5",
    timezone="America/Chicago",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="US",
    impersonate_target="chrome131",  # curl_cffi doesn't support firefox impersonation
)

_FIREFOX_132_LINUX_FEDORA = DeviceProfile(
    user_agent="Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    browser="firefox",
    browser_version="132",
    platform="Linux",
    locale="de-DE",
    accept_language="de-DE,de;q=0.9,en;q=0.5",
    timezone="Europe/Berlin",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="DE",
    impersonate_target="chrome131",  # curl_cffi doesn't support firefox impersonation
)

_EDGE_131_WIN_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.2903.86",
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

_BRAVE_131_WIN_US = DeviceProfile(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    browser="chrome",
    browser_version="131",
    platform="Windows",
    locale="en-US",
    accept_language="en-US,en;q=0.9",
    timezone="America/Denver",
    viewport={"width": 1920, "height": 1080},
    screen={"width": 1920, "height": 1080},
    color_depth=24,
    pixel_ratio=1.0,
    hardware_concurrency=8,
    geo_hint="US",
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
    # Sprint 5: new profiles
    _CHROME_131_ANDROID_SAMSUNG_S24,
    _CHROME_131_ANDROID_PIXEL_8,
    _CHROME_131_ANDROID_ONEPLUS_12,
    _CHROME_131_IOS_IPAD,
    _SAFARI_17_IOS_IPHONE15,
    _SAFARI_17_IOS_IPHONE14,
    _FIREFOX_132_LINUX_UBUNTU,
    _FIREFOX_132_LINUX_FEDORA,
    _EDGE_131_WIN_US,
    _BRAVE_131_WIN_US,
]


# =============================================================================
# UA Version Updater — bump all profiles to latest browser versions
# =============================================================================

# Current latest stable versions (update these quarterly)
LATEST_CHROME_VERSION = "131"
LATEST_FIREFOX_VERSION = "132"
LATEST_SAFARI_VERSION = "17.6"

# curl_cffi impersonate targets mapped to versions
CHROME_IMPERSONATE_MAP = {
    "131": "chrome131",
    "130": "chrome130",
    "124": "chrome124",
    "120": "chrome120",
}


def update_browser_versions(
    chrome_version: Optional[str] = None,
    firefox_version: Optional[str] = None,
    safari_version: Optional[str] = None,
) -> list[DeviceProfile]:
    """Generate updated profiles with new browser versions.

    Bumps the UA strings, browser_version, sec-ch-ua headers, and
    impersonate targets across all profiles while keeping everything
    else (locale, timezone, viewport, screen, geo) consistent.

    This is how you keep the UA database current without manually
    editing 14 profile definitions. Call quarterly.

    Args:
        chrome_version: New Chrome major version (e.g. "133")
        firefox_version: New Firefox major version (e.g. "134")
        safari_version: New Safari version (e.g. "18.0")

    Returns:
        New list of updated DeviceProfile objects.
    """
    import re as _re

    chrome_v = chrome_version or LATEST_CHROME_VERSION
    firefox_v = firefox_version or LATEST_FIREFOX_VERSION
    safari_v = safari_version or LATEST_SAFARI_VERSION

    # Determine curl_cffi impersonate target
    chrome_impersonate = CHROME_IMPERSONATE_MAP.get(chrome_v, f"chrome{chrome_v}")

    updated: list[DeviceProfile] = []

    for p in DEVICE_PROFILES:
        if p.browser == "chrome":
            # Update Chrome UA string
            new_ua = _re.sub(
                r"Chrome/\d+\.0\.0\.0",
                f"Chrome/{chrome_v}.0.0.0",
                p.user_agent,
            )
            updated.append(DeviceProfile(
                user_agent=new_ua,
                browser=p.browser,
                browser_version=chrome_v,
                platform=p.platform,
                locale=p.locale,
                accept_language=p.accept_language,
                timezone=p.timezone,
                viewport=p.viewport,
                screen=p.screen,
                color_depth=p.color_depth,
                pixel_ratio=p.pixel_ratio,
                hardware_concurrency=p.hardware_concurrency,
                geo_hint=p.geo_hint,
                impersonate_target=chrome_impersonate,
            ))
        elif p.browser == "firefox":
            # Update Firefox UA string
            new_ua = _re.sub(
                r"Firefox/\d+\.0",
                f"Firefox/{firefox_v}.0",
                p.user_agent,
            )
            new_ua = _re.sub(
                r"rv:\d+\.0",
                f"rv:{firefox_v}.0",
                new_ua,
            )
            updated.append(DeviceProfile(
                user_agent=new_ua,
                browser=p.browser,
                browser_version=firefox_v,
                platform=p.platform,
                locale=p.locale,
                accept_language=p.accept_language,
                timezone=p.timezone,
                viewport=p.viewport,
                screen=p.screen,
                color_depth=p.color_depth,
                pixel_ratio=p.pixel_ratio,
                hardware_concurrency=p.hardware_concurrency,
                geo_hint=p.geo_hint,
                impersonate_target=chrome_impersonate,  # curl_cffi doesn't support firefox
            ))
        elif p.browser == "safari":
            # Update Safari UA string
            new_ua = _re.sub(
                r"Version/[\d.]+",
                f"Version/{safari_v}",
                p.user_agent,
            )
            updated.append(DeviceProfile(
                user_agent=new_ua,
                browser=p.browser,
                browser_version=safari_v,
                platform=p.platform,
                locale=p.locale,
                accept_language=p.accept_language,
                timezone=p.timezone,
                viewport=p.viewport,
                screen=p.screen,
                color_depth=p.color_depth,
                pixel_ratio=p.pixel_ratio,
                hardware_concurrency=p.hardware_concurrency,
                geo_hint=p.geo_hint,
                impersonate_target=f"safari{safari_v.replace('.', '_')}",
            ))
        else:
            updated.append(p)

    return updated


def apply_version_update(
    chrome_version: Optional[str] = None,
    firefox_version: Optional[str] = None,
    safari_version: Optional[str] = None,
) -> None:
    """Update the global DEVICE_PROFILES list in-place with new versions.

    Call this at startup or periodically to keep UAs current:
        apply_version_update(chrome_version="133", firefox_version="134")
    """
    global DEVICE_PROFILES
    DEVICE_PROFILES[:] = update_browser_versions(chrome_version, firefox_version, safari_version)


def get_headers_for_profile(profile: DeviceProfile) -> dict[str, str]:
    """Build browser-realistic HTTP headers from a device profile.

    Header order matches real Chrome/Firefox output — this matters
    for header-order fingerprinting.
    """
    if profile.browser == "chrome":
        _is_mobile = profile.platform in ("Linux armv81", "iPhone", "iPad")
        return {
            "sec-ch-ua": f'"Chromium";v="{profile.browser_version}", "Google Chrome";v="{profile.browser_version}", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?1" if _is_mobile else "?0",
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
