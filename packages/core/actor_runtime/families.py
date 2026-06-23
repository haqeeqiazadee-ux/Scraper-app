from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Callable

from packages.core.actor_runtime.models import ActorSpec, ProviderStep
from packages.core.actor_runtime.runner import BaseActorRunner
from packages.core.interfaces import FetchRequest
from packages.core.secrets import SecretsManager


class ActorBaseFamily(StrEnum):
    GENERIC_WEB_PAGE_EXTRACTION = "generic_web_page_extraction"
    COMMERCE_STOREFRONT_GENERIC = "commerce_storefront_generic"
    MARKETPLACE_PRODUCT_CATALOG = "marketplace_product_catalog"
    LOCAL_MAPS_SERP = "local_maps_serp"


def _entry_text(entry: Any) -> str:
    values = [
        getattr(entry, "name", ""),
        getattr(entry, "title", ""),
        getattr(entry, "description", ""),
        " ".join(getattr(entry, "categories", ()) or ()),
    ]
    return " ".join(str(value).lower() for value in values if value)


def _is_amazon_family(entry: Any) -> bool:
    text = _entry_text(entry)
    return "amazon" in text


def determine_actor_family(entry: Any) -> str:
    route_strategy = getattr(entry, "route_strategy", "")
    if route_strategy != "native_pipeline":
        return route_strategy

    text = _entry_text(entry)
    if any(term in text for term in ("google maps", "maps business", "local business", "places", "near me")):
        return ActorBaseFamily.LOCAL_MAPS_SERP.value
    if any(term in text for term in ("amazon", "ebay", "walmart", "marketplace")):
        return ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG.value
    if any(term in text for term in ("shopify", "woocommerce", "ecommerce", "product", "storefront", "catalog", "price")):
        return ActorBaseFamily.COMMERCE_STOREFRONT_GENERIC.value
    return ActorBaseFamily.GENERIC_WEB_PAGE_EXTRACTION.value


def build_actor_spec(entry: Any) -> ActorSpec:
    family = determine_actor_family(entry)
    required_env_names: tuple[str, ...] = ()
    optional_env_names: tuple[str, ...] = ()
    provider_chain: tuple[ProviderStep, ...] = ()

    if family == ActorBaseFamily.GENERIC_WEB_PAGE_EXTRACTION:
        provider_chain = (ProviderStep(name="http_worker", priority=1),)
    elif family == ActorBaseFamily.COMMERCE_STOREFRONT_GENERIC:
        provider_chain = (
            ProviderStep(name="shopify_products_json", priority=1),
            ProviderStep(name="http_worker", priority=2),
        )
    elif family == ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG:
        if _is_amazon_family(entry):
            required_env_names = ("KEEPA_API_KEY",)
            provider_chain = (ProviderStep(name="keepa", required_env_names=("KEEPA_API_KEY",), priority=1),)
        else:
            provider_chain = (ProviderStep(name="http_worker", priority=1),)
    elif family == ActorBaseFamily.LOCAL_MAPS_SERP:
        optional_env_names = ("SERPER_API_KEY", "GOOGLE_MAPS_API_KEY")
        provider_chain = (
            ProviderStep(name="serper_places", required_env_names=("SERPER_API_KEY",), priority=1),
            ProviderStep(name="google_places", required_env_names=("GOOGLE_MAPS_API_KEY",), priority=2),
            ProviderStep(name="maps_browser_fallback", priority=3),
        )

    return ActorSpec(
        actor_id=getattr(entry, "actor_id"),
        slug=getattr(entry, "name", ""),
        title=getattr(entry, "title", ""),
        base_family=family,
        required_env_names=required_env_names,
        optional_env_names=optional_env_names,
        provider_chain=provider_chain,
        compliance_notes=(
            "Apify catalog URL is source metadata only; execution must use native Scraper-app stack.",
        ),
    )


def _target_from_payload(payload: dict[str, Any]) -> str:
    target = str(payload.get("target") or payload.get("url") or "").strip()
    if not target:
        raise ValueError("Actor input requires a target URL, url, or query field")
    return target


class GenericWebPageExtractionRunner(BaseActorRunner):
    def __init__(
        self,
        spec: ActorSpec,
        *,
        task_id: str,
        tenant_id: str,
        secrets_manager: SecretsManager | None = None,
    ) -> None:
        super().__init__(spec, secrets_manager=secrets_manager)
        self.task_id = task_id
        self.tenant_id = tenant_id

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run_http_worker(payload)

    async def _run_http_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        from services.worker_http.worker import HttpWorker

        target = _target_from_payload(payload)
        worker = HttpWorker()
        try:
            worker_result = await worker.process_task(
                {
                    "task_id": self.task_id,
                    "tenant_id": self.tenant_id,
                    "url": target,
                    "timeout_ms": int(payload.get("timeout_ms") or 30000),
                    "paginate": bool(payload.get("paginate") or (int(payload.get("max_pages") or 1) > 1)),
                    "max_pages": int(payload.get("max_pages") or 1),
                    "css_selectors": payload.get("css_selectors"),
                }
            )
        finally:
            await worker.close()

        if worker_result.get("status") != "success":
            raise RuntimeError(worker_result.get("error") or "Native HTTP extraction failed")

        return {
            "extracted_data": worker_result.get("extracted_data", []),
            "item_count": worker_result.get("item_count", 0),
            "confidence": worker_result.get("confidence", 0.0),
            "status_code": worker_result.get("status_code"),
            "extraction_method": worker_result.get("extraction_method", "deterministic"),
            "bytes_downloaded": worker_result.get("bytes_downloaded", 0),
            "duration_ms": worker_result.get("duration_ms", 0),
            "artifacts": worker_result.get("artifacts", []),
        }


class CommerceStorefrontGenericRunner(GenericWebPageExtractionRunner):
    def __init__(
        self,
        spec: ActorSpec,
        *,
        task_id: str,
        tenant_id: str,
        secrets_manager: SecretsManager | None = None,
        shopify_factory: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__(spec, task_id=task_id, tenant_id=tenant_id, secrets_manager=secrets_manager)
        self._shopify_factory = shopify_factory

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = _target_from_payload(payload)
        max_results = int(payload.get("max_results") or payload.get("limit") or 50)
        connector = self._create_shopify_connector()
        try:
            products = await connector.get_store_products(
                target,
                limit=max_results,
                collection=payload.get("collection"),
            )
        finally:
            close = getattr(connector, "close", None)
            if close is not None:
                await close()

        if products:
            return {
                "extracted_data": products,
                "item_count": len(products),
                "confidence": 0.95,
                "status_code": 200,
                "extraction_method": "shopify_products_json",
                "bytes_downloaded": 0,
                "duration_ms": 0,
                "artifacts": [],
            }
        return await self._run_http_worker(payload)

    def _create_shopify_connector(self) -> Any:
        if self._shopify_factory is not None:
            return self._shopify_factory()
        from packages.connectors.shopify_connector import ShopifyConnector

        return ShopifyConnector()


class MarketplaceProductCatalogRunner(GenericWebPageExtractionRunner):
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = _target_from_payload(payload)
        if "amazon." not in target.lower():
            return await self._run_http_worker(payload)

        from packages.connectors.keepa_connector import KeepaConnector

        connector = KeepaConnector()
        response = await connector.fetch(FetchRequest(url=target, timeout_ms=int(payload.get("timeout_ms") or 30000)))
        if not response.ok:
            raise RuntimeError(response.error or "Keepa returned no marketplace products")
        products = json.loads(response.text or "[]")
        return {
            "extracted_data": products,
            "item_count": len(products),
            "confidence": 0.95,
            "status_code": response.status_code,
            "extraction_method": "keepa",
            "bytes_downloaded": len(response.body or b""),
            "duration_ms": 0,
            "artifacts": [],
        }


class LocalMapsSerpRunner(BaseActorRunner):
    def __init__(
        self,
        spec: ActorSpec,
        *,
        task_id: str,
        tenant_id: str,
        secrets_manager: SecretsManager | None = None,
        maps_factory: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__(spec, secrets_manager=secrets_manager)
        self.task_id = task_id
        self.tenant_id = tenant_id
        self._maps_factory = maps_factory

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query") or payload.get("target") or "").strip()
        if not query:
            raise ValueError("Local maps actor input requires a query or target field")

        connector = self._create_maps_connector()
        try:
            results = await connector.search_businesses(
                query=query,
                max_results=int(payload.get("max_results") or payload.get("limit") or 20),
                location=payload.get("location"),
                language=str(payload.get("language") or "en"),
            )
        finally:
            close = getattr(connector, "close", None)
            if close is not None:
                await close()

        return {
            "extracted_data": results,
            "item_count": len(results),
            "confidence": 0.9 if results else 0.0,
            "status_code": 200,
            "extraction_method": "google_maps_connector",
            "bytes_downloaded": 0,
            "duration_ms": 0,
            "artifacts": [],
        }

    def _create_maps_connector(self) -> Any:
        if self._maps_factory is not None:
            return self._maps_factory()
        from packages.connectors.google_maps_connector import GoogleMapsConnector

        return GoogleMapsConnector()


def create_actor_runner(
    spec: ActorSpec,
    entry: Any,
    *,
    task_id: str,
    tenant_id: str,
    secrets_manager: SecretsManager | None = None,
) -> BaseActorRunner:
    if spec.base_family == ActorBaseFamily.COMMERCE_STOREFRONT_GENERIC:
        return CommerceStorefrontGenericRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG:
        return MarketplaceProductCatalogRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.LOCAL_MAPS_SERP:
        return LocalMapsSerpRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    return GenericWebPageExtractionRunner(
        spec,
        task_id=task_id,
        tenant_id=tenant_id,
        secrets_manager=secrets_manager,
    )
