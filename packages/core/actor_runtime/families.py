from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Callable
from urllib.parse import urlparse

from packages.core.actor_runtime.models import ActorSpec, ProviderStep
from packages.core.actor_runtime.runner import BaseActorRunner
from packages.core.interfaces import FetchRequest
from packages.core.secrets import SecretsManager


class ActorBaseFamily(StrEnum):
    GENERIC_WEB_PAGE_EXTRACTION = "generic_web_page_extraction"
    COMMERCE_STOREFRONT_GENERIC = "commerce_storefront_generic"
    MARKETPLACE_PRODUCT_CATALOG = "marketplace_product_catalog"
    LOCAL_MAPS_SERP = "local_maps_serp"
    JOB_BOARD_SCHEMA = "job_board_schema"
    REAL_ESTATE_SCHEMA = "real_estate_schema"
    LEAD_GENERATION_GENERIC = "lead_generation_generic"
    REVIEW_MONITORING_GENERIC = "review_monitoring_generic"
    NEWS_CONTENT_MONITORING = "news_content_monitoring"


def _entry_text(entry: Any) -> str:
    values = [
        getattr(entry, "name", ""),
        getattr(entry, "title", ""),
        getattr(entry, "description", ""),
        " ".join(getattr(entry, "categories", ()) or ()),
    ]
    return " ".join(str(value).lower() for value in values if value)


def _entry_categories(entry: Any) -> set[str]:
    return {str(value).upper() for value in (getattr(entry, "categories", ()) or ())}


def _is_amazon_family(entry: Any) -> bool:
    text = _entry_text(entry)
    return "amazon" in text


def determine_actor_family(entry: Any) -> str:
    route_strategy = getattr(entry, "route_strategy", "")
    if route_strategy == "job_board_schema":
        return ActorBaseFamily.JOB_BOARD_SCHEMA.value
    if route_strategy == "real_estate_schema":
        return ActorBaseFamily.REAL_ESTATE_SCHEMA.value
    if route_strategy != "native_pipeline":
        return route_strategy

    text = _entry_text(entry)
    categories = _entry_categories(entry)
    if any(term in text for term in ("google maps", "maps business", "local business", "places", "near me")):
        return ActorBaseFamily.LOCAL_MAPS_SERP.value
    if any(term in text for term in ("amazon", "ebay", "walmart", "marketplace")):
        return ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG.value
    if "NEWS" in categories or any(term in text for term in ("news", "article", "blog", "rss", "content monitor")):
        return ActorBaseFamily.NEWS_CONTENT_MONITORING.value
    if "review" in text or "reviews" in text or any(term in text for term in ("trustpilot", "yelp", "ratings")):
        return ActorBaseFamily.REVIEW_MONITORING_GENERIC.value
    if "LEAD_GENERATION" in categories or any(
        term in text for term in ("lead", "leads", "email", "phone", "contact", "prospecting")
    ):
        return ActorBaseFamily.LEAD_GENERATION_GENERIC.value
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
    elif family in (ActorBaseFamily.JOB_BOARD_SCHEMA, ActorBaseFamily.REAL_ESTATE_SCHEMA):
        provider_chain = (ProviderStep(name="http_worker_schema_match", priority=1),)
    elif family == ActorBaseFamily.LEAD_GENERATION_GENERIC:
        provider_chain = (ProviderStep(name="http_worker_contacts", priority=1),)
    elif family == ActorBaseFamily.REVIEW_MONITORING_GENERIC:
        provider_chain = (ProviderStep(name="http_worker_reviews", priority=1),)
    elif family == ActorBaseFamily.NEWS_CONTENT_MONITORING:
        provider_chain = (ProviderStep(name="http_worker_content_monitoring", priority=1),)

    output_schema: dict[str, Any] = {}
    if family == ActorBaseFamily.JOB_BOARD_SCHEMA:
        from packages.contracts.schemas.job_board import JobListing

        output_schema = JobListing.model_json_schema()
    elif family == ActorBaseFamily.REAL_ESTATE_SCHEMA:
        from packages.contracts.schemas.real_estate import RealEstateListing

        output_schema = RealEstateListing.model_json_schema()

    return ActorSpec(
        actor_id=getattr(entry, "actor_id"),
        slug=getattr(entry, "name", ""),
        title=getattr(entry, "title", ""),
        base_family=family,
        output_schema=output_schema,
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


def _first_value(item: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        for key, value in item.items():
            clean_key = str(key).lower().replace("-", "_").strip()
            if clean_key == alias or clean_key.endswith(f"_{alias}"):
                if value not in (None, ""):
                    return value
    return None


def _source_from_item(item: dict[str, Any], fallback_url: str) -> str:
    value = _first_value(item, ("source", "platform", "site"))
    if value:
        return str(value)
    host = urlparse(fallback_url).netloc
    return host or "unknown"


def _list_value(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [str(value)]


def _float_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    from packages.core.normalizer import clean_price

    cleaned = clean_price(str(value))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    parsed = _float_value(value)
    return int(parsed) if parsed is not None else None


def _schema_match_summary(item: dict[str, Any], required_fields: tuple[str, ...]) -> dict[str, Any]:
    matched = {field: item.get(field) for field in required_fields if item.get(field) not in (None, "", [], {})}
    return {
        "matched_fields": matched,
        "match_confidence": round(len(matched) / len(required_fields), 4) if required_fields else 0.0,
    }


def _has_contact_signal(item: dict[str, Any]) -> bool:
    item_str = str(item).lower()
    if any(term in item_str for term in ("@", "phone", "email", "contact", "address", "tel:", "mailto:")):
        return True
    url = str(item.get("url") or item.get("product_url") or "").lower()
    return any(site in url for site in ("linkedin", "twitter", "facebook", "instagram", "github"))


def _has_review_signal(item: dict[str, Any]) -> bool:
    keys = {str(key).lower() for key in item}
    if keys & {"review_title", "review_text", "reviewer_name", "reviewer", "stars", "score", "rating"}:
        return True
    item_str = str(item).lower()
    return "review" in item_str or "rating" in item_str


def _has_content_signal(item: dict[str, Any]) -> bool:
    category = str(item.get("_category") or "").lower()
    if category in {"content", "heading", "testimonial", "stat", "metadata", "article"}:
        return True
    if item.get("content_type") == "article" or item.get("full_content") or item.get("article_body"):
        return True
    return bool(item.get("heading_level"))


class GenericWebPageExtractionRunner(BaseActorRunner):
    def __init__(
        self,
        spec: ActorSpec,
        *,
        task_id: str,
        tenant_id: str,
        secrets_manager: SecretsManager | None = None,
        http_worker_factory: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__(spec, secrets_manager=secrets_manager)
        self.task_id = task_id
        self.tenant_id = tenant_id
        self._http_worker_factory = http_worker_factory

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._run_http_worker(payload)

    async def _run_http_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = _target_from_payload(payload)
        worker = self._create_http_worker()
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

    def _create_http_worker(self) -> Any:
        if self._http_worker_factory is not None:
            return self._http_worker_factory()
        from services.worker_http.worker import HttpWorker

        return HttpWorker()


class _HttpWorkerPostProcessorRunner(GenericWebPageExtractionRunner):
    extraction_method = "http_worker"

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = await self._run_http_worker(payload)
        target = _target_from_payload(payload)
        items = self._post_process_items(output.get("extracted_data", []), target)
        output.update(
            {
                "extracted_data": items,
                "item_count": len(items),
                "extraction_method": self.extraction_method,
            }
        )
        return output

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        return items


class JobBoardSchemaRunner(_HttpWorkerPostProcessorRunner):
    extraction_method = "job_board_schema"

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        from packages.contracts.schemas.job_board import JobCompensation, JobListing, JobLocation

        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            location_raw = _first_value(item, ("location", "job_location"))
            location = location_raw if isinstance(location_raw, dict) else {}
            if isinstance(location_raw, str):
                location = {
                    "city": location_raw,
                    "remote": "remote" in location_raw.lower(),
                    "hybrid": "hybrid" in location_raw.lower(),
                }

            compensation_raw = _first_value(item, ("compensation", "salary", "salary_range"))
            compensation = compensation_raw if isinstance(compensation_raw, dict) else {}
            if isinstance(compensation_raw, str):
                compensation = {"period": compensation_raw}

            candidate = {
                "id": _first_value(item, ("id", "job_id")),
                "url": _first_value(item, ("url", "job_url", "apply_url", "link", "product_url")) or target,
                "title": _first_value(item, ("title", "job_title", "name")),
                "company_name": _first_value(item, ("company_name", "company", "employer", "hiring_organization")),
                "company_url": _first_value(item, ("company_url", "employer_url")),
                "location": JobLocation(**location).model_dump(mode="json"),
                "compensation": JobCompensation(**compensation).model_dump(mode="json"),
                "employment_type": _first_value(item, ("employment_type", "job_type")),
                "seniority_level": _first_value(item, ("seniority_level", "seniority")),
                "description": _first_value(item, ("description", "job_description", "text", "content", "summary")),
                "requirements": _list_value(_first_value(item, ("requirements", "skills_required", "skills"))),
                "benefits": _list_value(_first_value(item, ("benefits", "perks"))),
                "posted_at": _first_value(item, ("posted_at", "posted_date", "date_posted")),
                "scraped_at": _first_value(item, ("scraped_at", "extracted_at")),
                "source": _source_from_item(item, target),
            }
            candidate = {key: value for key, value in candidate.items() if value is not None}
            try:
                normalized.append(JobListing(**candidate).model_dump(mode="json", exclude_none=True))
            except Exception:
                continue
        return normalized

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = await super().execute(payload)
        items = output.get("extracted_data", [])
        output["schema_matched"] = _schema_match_summary(
            items[0] if items else {},
            ("url", "title", "company_name", "description", "source"),
        )
        return output


class RealEstateSchemaRunner(_HttpWorkerPostProcessorRunner):
    extraction_method = "real_estate_schema"

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        from packages.contracts.schemas.real_estate import PropertyAddress, PropertyFeatures, RealEstateListing

        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            address_raw = _first_value(item, ("address", "property_address"))
            address = address_raw if isinstance(address_raw, dict) else {}
            if isinstance(address_raw, str):
                address = {"street": address_raw}

            features_raw = _first_value(item, ("features", "property_features"))
            features = dict(features_raw) if isinstance(features_raw, dict) else {}
            features.setdefault("bedrooms", _float_value(_first_value(item, ("bedrooms", "beds"))))
            features.setdefault("bathrooms", _float_value(_first_value(item, ("bathrooms", "baths"))))
            features.setdefault("square_feet", _float_value(_first_value(item, ("square_feet", "sqft", "area"))))
            features.setdefault("lot_size", _float_value(_first_value(item, ("lot_size", "lot"))))
            features.setdefault("year_built", _int_value(_first_value(item, ("year_built",))))
            features.setdefault("property_type", _first_value(item, ("property_type", "type")))

            candidate = {
                "id": _first_value(item, ("id", "property_id", "listing_id")),
                "url": _first_value(item, ("url", "property_url", "listing_url", "link", "product_url")) or target,
                "title": _first_value(item, ("title", "name", "headline")),
                "price": _float_value(_first_value(item, ("price", "listing_price", "amount"))),
                "currency": _first_value(item, ("currency",)) or "USD",
                "status": _first_value(item, ("status", "listing_status")),
                "address": PropertyAddress(**address).model_dump(mode="json"),
                "features": PropertyFeatures(**features).model_dump(mode="json"),
                "description": _first_value(item, ("description", "property_description", "summary", "content")),
                "images": _list_value(_first_value(item, ("images", "image_urls", "image_url", "photo"))),
                "agent_name": _first_value(item, ("agent_name", "agent")),
                "agent_phone": _first_value(item, ("agent_phone", "phone")),
                "agency_name": _first_value(item, ("agency_name", "brokerage")),
                "days_on_market": _int_value(_first_value(item, ("days_on_market",))),
                "scraped_at": _first_value(item, ("scraped_at", "extracted_at")),
                "source": _source_from_item(item, target),
            }
            candidate = {key: value for key, value in candidate.items() if value is not None}
            try:
                normalized.append(RealEstateListing(**candidate).model_dump(mode="json", exclude_none=True))
            except Exception:
                continue
        return normalized

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = await super().execute(payload)
        items = output.get("extracted_data", [])
        output["schema_matched"] = _schema_match_summary(
            items[0] if items else {},
            ("url", "title", "description", "source"),
        )
        return output


class LeadGenerationGenericRunner(_HttpWorkerPostProcessorRunner):
    extraction_method = "lead_generation_generic"

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        return [item for item in items if isinstance(item, dict) and _has_contact_signal(item)]


class ReviewMonitoringGenericRunner(_HttpWorkerPostProcessorRunner):
    extraction_method = "review_monitoring_generic"

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        return [item for item in items if isinstance(item, dict) and _has_review_signal(item)]


class NewsContentMonitoringRunner(_HttpWorkerPostProcessorRunner):
    extraction_method = "news_content_monitoring"

    def _post_process_items(self, items: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
        return [item for item in items if isinstance(item, dict) and _has_content_signal(item)]


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
    if spec.base_family == ActorBaseFamily.JOB_BOARD_SCHEMA:
        return JobBoardSchemaRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.REAL_ESTATE_SCHEMA:
        return RealEstateSchemaRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.LEAD_GENERATION_GENERIC:
        return LeadGenerationGenericRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.REVIEW_MONITORING_GENERIC:
        return ReviewMonitoringGenericRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            secrets_manager=secrets_manager,
        )
    if spec.base_family == ActorBaseFamily.NEWS_CONTENT_MONITORING:
        return NewsContentMonitoringRunner(
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
