"""
Connector adapters for the AI Scraping Platform.

Each connector implements the Connector protocol from packages.core.interfaces.
Connectors are pluggable — add new ones by implementing the protocol.
"""

from packages.connectors.http_collector import HttpCollector
from packages.connectors.browser_worker import PlaywrightBrowserWorker
from packages.connectors.hard_target_worker import HardTargetWorker
from packages.connectors.proxy_adapter import ProxyAdapter
from packages.connectors.captcha_adapter import CaptchaAdapter
from packages.connectors.api_adapter import ApiAdapter
from packages.connectors.keepa_connector import KeepaConnector

__all__ = [
    "HttpCollector",
    "PlaywrightBrowserWorker",
    "HardTargetWorker",
    "ProxyAdapter",
    "CaptchaAdapter",
    "ApiAdapter",
    "KeepaConnector",
]
