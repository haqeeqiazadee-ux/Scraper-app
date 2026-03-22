"""
OpenTelemetry Tracing — distributed tracing for the scraping platform.

Provides trace context propagation across services (control-plane, workers).
Falls back gracefully when opentelemetry SDK is not installed.
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry; fall back to no-op if not available
_otel_available = False
try:
    from opentelemetry import trace
    from opentelemetry.trace import StatusCode, Span
    _otel_available = True
except ImportError:
    pass


class NoOpSpan:
    """No-op span when OpenTelemetry is not installed."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any, description: str = "") -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class Tracer:
    """Platform tracer that wraps OpenTelemetry or provides no-op fallback."""

    def __init__(self, service_name: str = "scraper-platform") -> None:
        self._service_name = service_name
        self._tracer = None
        if _otel_available:
            self._tracer = trace.get_tracer(service_name)

    @contextmanager
    def span(self, name: str, attributes: dict | None = None):
        """Create a traced span."""
        if self._tracer:
            with self._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                yield span
        else:
            yield NoOpSpan()

    def trace(self, name: Optional[str] = None, attributes: dict | None = None) -> Callable:
        """Decorator to trace a function call."""
        def decorator(func: Callable) -> Callable:
            span_name = name or f"{func.__module__}.{func.__qualname__}"

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.span(span_name, attributes) as span:
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        if _otel_available:
                            span.set_status(StatusCode.ERROR, str(e))
                        raise

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.span(span_name, attributes) as span:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        if _otel_available:
                            span.set_status(StatusCode.ERROR, str(e))
                        raise

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator


class SpanRecorder:
    """Records spans locally for testing and debugging without OTel collector."""

    def __init__(self) -> None:
        self._spans: list[dict] = []

    def record(self, name: str, duration_ms: float, attributes: dict | None = None, error: str = "") -> None:
        self._spans.append({
            "name": name,
            "duration_ms": duration_ms,
            "attributes": attributes or {},
            "error": error,
            "timestamp": time.time(),
        })

    @property
    def spans(self) -> list[dict]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()

    def find(self, name: str) -> list[dict]:
        return [s for s in self._spans if s["name"] == name]


def configure_tracing(
    service_name: str = "scraper-platform",
    endpoint: str = "",
    enabled: bool = True,
) -> Tracer:
    """
    Configure OpenTelemetry tracing for the service.

    If OTel is not installed or enabled=False, returns a no-op tracer.
    """
    if not enabled or not _otel_available:
        logger.info("Tracing disabled or opentelemetry not installed")
        return Tracer(service_name)

    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=endpoint)
            except ImportError:
                logger.warning("OTLP exporter not available, using console")
                exporter = ConsoleSpanExporter()
        else:
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("Tracing configured", extra={"service": service_name, "endpoint": endpoint or "console"})
    except Exception as e:
        logger.warning("Failed to configure tracing", extra={"error": str(e)})

    return Tracer(service_name)


# Default tracer instance
tracer = Tracer()
