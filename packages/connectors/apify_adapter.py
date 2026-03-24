"""
Apify Adapter — connector for running Apify actors to scrape video/social platforms.

Maps template IDs to the best Apify actor for each use case.
Implements the Connector protocol for the Apify execution lane.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from packages.core.interfaces import ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template → Apify Actor mapping
# ---------------------------------------------------------------------------

@dataclass
class ApifyActorConfig:
    """Configuration for a specific Apify actor."""

    actor_id: str
    name: str
    default_input: dict[str, Any] = field(default_factory=dict)
    max_items: int = 10
    timeout_secs: int = 120
    memory_mbytes: int = 256


# Best actor for each template, selected by popularity & reliability from Apify store
TEMPLATE_ACTOR_MAP: dict[str, ApifyActorConfig] = {
    # YouTube ecosystem
    "youtube-video": ApifyActorConfig(
        actor_id="h7sDV53CddomktSi5",
        name="YouTube Scraper",
        default_input={"maxResults": 5, "type": "video"},
    ),
    "youtube-channel": ApifyActorConfig(
        actor_id="67Q6fmd8iedTVcCwY",
        name="Fast YouTube Channel Scraper",
        default_input={"maxResults": 5},
    ),
    "youtube-comments": ApifyActorConfig(
        actor_id="p7UMdpQnjKmmpR21D",
        name="YouTube Comments Scraper",
        default_input={"maxResults": 10},
    ),
    "youtube-transcript": ApifyActorConfig(
        actor_id="1s7eXiaukVuOr4Ueg",
        name="Youtube Transcripts",
        default_input={"maxResults": 3},
    ),
    "youtube-shorts": ApifyActorConfig(
        actor_id="WT1BVWatl2aHVeFEH",
        name="YouTube Shorts Scraper",
        default_input={"maxResults": 5},
    ),
    "youtube-search": ApifyActorConfig(
        actor_id="nfyn3ecod9uCDaoVH",
        name="YouTube Search Scraper",
        default_input={"maxResults": 5},
    ),
    "youtube-trending": ApifyActorConfig(
        actor_id="jnHyoAspdnYdE42rn",
        name="Fast YouTube Trending Scraper API",
        default_input={"maxResults": 5},
    ),
    "youtube-downloader": ApifyActorConfig(
        actor_id="y1IMcEPawMQPafm02",
        name="Youtube Video Downloader",
        default_input={},
    ),
    # TikTok ecosystem
    "tiktok-video": ApifyActorConfig(
        actor_id="S5h7zRLfKFEr8pdj7",
        name="TikTok Video Scraper",
        default_input={"maxResults": 5},
    ),
    "tiktok-profile": ApifyActorConfig(
        actor_id="0FXVyOXXEmdGcV88a",
        name="TikTok Profile Scraper",
        default_input={"maxResults": 5},
    ),
    "tiktok-comments": ApifyActorConfig(
        actor_id="BDec00yAmCm1QbMEI",
        name="TikTok Comments Scraper",
        default_input={"maxResults": 10},
    ),
    "tiktok-hashtag": ApifyActorConfig(
        actor_id="f1ZeP0K58iwlqG2pY",
        name="TikTok Hashtag Scraper",
        default_input={"maxResults": 5},
    ),
    "tiktok-trending": ApifyActorConfig(
        actor_id="sDvA9jM4WRTDX4Syr",
        name="TikTok Trends Scraper",
        default_input={"maxResults": 5},
    ),
    "tiktok-sound": ApifyActorConfig(
        actor_id="JVisUAY6oGn2dBn99",
        name="TikTok Sound Scraper",
        default_input={"maxResults": 5},
    ),
    # Instagram ecosystem
    "instagram-reel": ApifyActorConfig(
        actor_id="xMc5Ga1oCONPmWJIa",
        name="Instagram Reel Scraper",
        default_input={"maxResults": 5},
    ),
    "instagram-stories": ApifyActorConfig(
        actor_id="xbcy7vii3udafaGiT",
        name="Instagram Stories Downloader Scraper",
        default_input={"maxResults": 5},
    ),
    "instagram-video-downloader": ApifyActorConfig(
        actor_id="OWBUCWZK5MEeO5XiC",
        name="Instagram Video Downloader",
        default_input={},
    ),
    # Facebook
    "facebook-reels": ApifyActorConfig(
        actor_id="5CvjfVGyTzrrG3sWx",
        name="Facebook Reels Scraper",
        default_input={"maxResults": 5},
    ),
    # Multi-platform
    "multi-platform-transcriber": ApifyActorConfig(
        actor_id="CVQmx5Se22zxPaWc1",
        name="TikTok | Instagram | Facebook | YouTube Shorts Transcriber",
        default_input={"maxResults": 3},
    ),
    "multi-platform-downloader": ApifyActorConfig(
        actor_id="iZbsVYT4VfdMxoIPL",
        name="All-in-One Media Downloader",
        default_input={},
    ),
}


def get_actor_for_template(template_id: str) -> ApifyActorConfig | None:
    """Return the Apify actor config for a given template ID."""
    return TEMPLATE_ACTOR_MAP.get(template_id)


def list_supported_templates() -> list[str]:
    """Return all template IDs that have Apify actor mappings."""
    return list(TEMPLATE_ACTOR_MAP.keys())


# ---------------------------------------------------------------------------
# Apify Adapter (Connector protocol)
# ---------------------------------------------------------------------------


class ApifyAdapter:
    """Connector for running Apify actors.

    Usage:
        adapter = ApifyAdapter(api_token="apify_api_xxx")
        response = await adapter.run_actor("youtube-video", {"searchKeywords": "python"})
    """

    def __init__(self, api_token: str) -> None:
        self._api_token = api_token
        self._metrics = ConnectorMetrics()
        self._client = None
        self._credits_used: float = 0.0

    async def _get_client(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize httpx client for Apify REST API."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                base_url="https://api.apify.com/v2",
                headers={"Authorization": f"Bearer {self._api_token}"},
                timeout=180.0,
            )
        return self._client

    async def run_actor(
        self,
        template_id: str,
        actor_input: dict[str, Any] | None = None,
        *,
        max_items: int | None = None,
        timeout_secs: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run an Apify actor mapped to a template and return dataset items.

        Args:
            template_id: Template ID (e.g. "youtube-video")
            actor_input: Override/merge with default actor input
            max_items: Max items to fetch from dataset (overrides actor default)
            timeout_secs: Actor run timeout (overrides actor default)

        Returns:
            List of result dicts from the actor's dataset.
        """
        config = get_actor_for_template(template_id)
        if config is None:
            raise ValueError(
                f"No Apify actor mapping for template '{template_id}'. "
                f"Supported: {list_supported_templates()}"
            )

        merged_input = {**config.default_input}
        if actor_input:
            merged_input.update(actor_input)

        effective_timeout = timeout_secs or config.timeout_secs
        effective_max_items = max_items or config.max_items

        client = await self._get_client()
        self._metrics.total_requests += 1
        start = time.monotonic()

        try:
            # Start actor run (synchronous mode — waits for completion)
            run_response = await client.post(
                f"/acts/{config.actor_id}/runs",
                json=merged_input,
                params={"timeout": effective_timeout, "waitForFinish": effective_timeout},
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data["data"]["id"]
            status = run_data["data"]["status"]

            elapsed = int((time.monotonic() - start) * 1000)
            logger.info(
                "Apify actor run completed",
                extra={
                    "actor": config.name,
                    "actor_id": config.actor_id,
                    "run_id": run_id,
                    "status": status,
                    "elapsed_ms": elapsed,
                },
            )

            if status not in ("SUCCEEDED", "RUNNING"):
                self._metrics.failed_requests += 1
                self._metrics.last_error = f"Actor run {status}: {run_id}"
                return []

            # Fetch dataset items
            dataset_id = run_data["data"]["defaultDatasetId"]
            items_response = await client.get(
                f"/datasets/{dataset_id}/items",
                params={"limit": effective_max_items, "format": "json"},
            )
            items_response.raise_for_status()
            items = items_response.json()

            self._metrics.successful_requests += 1

            # Track usage
            usage = run_data["data"].get("usageTotalUsd", 0)
            self._credits_used += usage

            return items if isinstance(items, list) else []

        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning(
                "Apify actor run failed",
                extra={"template_id": template_id, "error": str(e), "elapsed_ms": elapsed},
            )
            return []

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Implement Connector protocol — route through best Apify actor.

        The request.metadata dict should contain:
            - template_id: which template/actor to use
            - actor_input: optional override input for the actor
        """
        template_id = request.metadata.get("template_id", "")
        actor_input = request.metadata.get("actor_input", {})

        if not template_id:
            return FetchResponse(
                url=request.url,
                status_code=400,
                error="Missing 'template_id' in request.metadata",
            )

        # Add URL to actor input if not already present
        if request.url and "url" not in actor_input:
            actor_input["urls"] = [request.url]

        start = time.monotonic()
        items = await self.run_actor(template_id, actor_input)
        elapsed = int((time.monotonic() - start) * 1000)

        if not items:
            return FetchResponse(
                url=request.url,
                status_code=204,
                text="[]",
                elapsed_ms=elapsed,
                error="No results from Apify actor",
            )

        text = json.dumps(items, ensure_ascii=False)
        return FetchResponse(
            url=request.url,
            status_code=200,
            text=text,
            body=text.encode(),
            elapsed_ms=elapsed,
        )

    async def health_check(self) -> bool:
        """Check connectivity to Apify API."""
        try:
            client = await self._get_client()
            resp = await client.get("/users/me")
            return resp.status_code == 200
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    @property
    def credits_used(self) -> float:
        """Total Apify credits consumed."""
        return self._credits_used

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
