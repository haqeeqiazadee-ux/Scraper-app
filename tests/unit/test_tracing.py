"""Tests for tracing module — works without OpenTelemetry installed."""

from __future__ import annotations

import pytest

from packages.core.tracing import Tracer, NoOpSpan, SpanRecorder, configure_tracing


class TestNoOpSpan:
    def test_context_manager(self):
        span = NoOpSpan()
        with span as s:
            s.set_attribute("key", "value")
            s.add_event("test_event")
            s.end()

    def test_no_op_methods(self):
        span = NoOpSpan()
        span.set_attribute("key", "value")
        span.set_status(None, "ok")
        span.record_exception(ValueError("test"))
        span.add_event("test", {"k": "v"})
        span.end()


class TestTracer:
    def test_span_context_manager(self):
        tracer = Tracer("test-service")
        with tracer.span("test-span") as span:
            assert span is not None

    def test_span_with_attributes(self):
        tracer = Tracer("test-service")
        with tracer.span("test-span", {"key": "value"}) as span:
            span.set_attribute("another", "attr")

    def test_trace_decorator_sync(self):
        tracer = Tracer("test-service")

        @tracer.trace("my-operation")
        def my_func(x: int) -> int:
            return x * 2

        assert my_func(5) == 10

    @pytest.mark.asyncio
    async def test_trace_decorator_async(self):
        tracer = Tracer("test-service")

        @tracer.trace("my-async-op")
        async def my_async_func(x: int) -> int:
            return x + 1

        result = await my_async_func(10)
        assert result == 11

    def test_trace_decorator_preserves_exceptions(self):
        tracer = Tracer("test-service")

        @tracer.trace()
        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            failing_func()

    @pytest.mark.asyncio
    async def test_trace_async_preserves_exceptions(self):
        tracer = Tracer("test-service")

        @tracer.trace()
        async def failing_async():
            raise RuntimeError("async error")

        with pytest.raises(RuntimeError, match="async error"):
            await failing_async()

    def test_trace_decorator_default_name(self):
        tracer = Tracer("test-service")

        @tracer.trace()
        def named_function():
            return True

        assert named_function() is True
        assert named_function.__name__ == "named_function"


class TestSpanRecorder:
    def test_record_and_retrieve(self):
        recorder = SpanRecorder()
        recorder.record("fetch", 150.0, {"url": "https://example.com"})
        recorder.record("extract", 50.0, {"method": "deterministic"})

        assert len(recorder.spans) == 2
        assert recorder.spans[0]["name"] == "fetch"
        assert recorder.spans[0]["duration_ms"] == 150.0
        assert recorder.spans[1]["attributes"]["method"] == "deterministic"

    def test_find_by_name(self):
        recorder = SpanRecorder()
        recorder.record("fetch", 100.0)
        recorder.record("extract", 50.0)
        recorder.record("fetch", 200.0)

        fetches = recorder.find("fetch")
        assert len(fetches) == 2

    def test_clear(self):
        recorder = SpanRecorder()
        recorder.record("span1", 10.0)
        recorder.record("span2", 20.0)
        recorder.clear()
        assert len(recorder.spans) == 0

    def test_record_with_error(self):
        recorder = SpanRecorder()
        recorder.record("failing-op", 30.0, error="Connection timeout")

        spans = recorder.find("failing-op")
        assert spans[0]["error"] == "Connection timeout"


class TestConfigureTracing:
    def test_configure_disabled(self):
        tracer = configure_tracing(enabled=False)
        assert isinstance(tracer, Tracer)

    def test_configure_default(self):
        tracer = configure_tracing()
        assert isinstance(tracer, Tracer)
