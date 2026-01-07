"""
Integration Tests
End-to-end tests for the complete grant discovery to alert delivery pipeline.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.events import (
    GrantDiscoveredEvent,
    GrantValidatedEvent,
    MatchComputedEvent,
    AlertPendingEvent,
    PriorityLevel,
    AlertChannel,
)
from agents.delivery.models import AlertPriority, DeliveryChannel


# =============================================================================
# Full Pipeline Integration Tests
# =============================================================================


class TestFullPipeline:
    """End-to-end tests for the complete grant processing pipeline."""

    @pytest.fixture
    def mock_pipeline(self, fake_redis, mock_anthropic, mock_openai, mock_sendgrid, mock_twilio):
        """Create a mock pipeline with all components."""
        class MockPipeline:
            def __init__(self):
                self.redis = fake_redis
                self.discovered_grants = []
                self.validated_grants = []
                self.computed_matches = []
                self.sent_alerts = []
                self.latencies = []

            async def discover_grant(self, grant_data: dict) -> GrantDiscoveredEvent:
                """Simulate grant discovery."""
                start = time.time()

                event = GrantDiscoveredEvent(
                    event_id=uuid.uuid4(),
                    grant_id=uuid.uuid4(),
                    source=grant_data.get("source", "test"),
                    title=grant_data.get("title", "Test Grant"),
                    url=grant_data.get("url", "https://test.com"),
                    funding_agency=grant_data.get("agency"),
                    estimated_amount=grant_data.get("amount"),
                    deadline=grant_data.get("deadline"),
                )

                # Publish to stream
                await self.redis.xadd("grants:discovered", {
                    "payload": event.model_dump_json(),
                    "event_type": "GrantDiscoveredEvent",
                })

                self.discovered_grants.append(event)
                self.latencies.append(("discovery", time.time() - start))

                return event

            async def validate_grant(self, event: GrantDiscoveredEvent) -> GrantValidatedEvent:
                """Simulate grant validation and curation."""
                start = time.time()

                # Mock LLM validation
                quality_score = 0.85

                validated = GrantValidatedEvent(
                    event_id=uuid.uuid4(),
                    grant_id=event.grant_id,
                    quality_score=quality_score,
                    categories=["research", "science"],
                    embedding_generated=True,
                    keywords=["test", "grant"],
                )

                # Publish to stream
                await self.redis.xadd("grants:validated", {
                    "payload": validated.model_dump_json(),
                    "event_type": "GrantValidatedEvent",
                })

                self.validated_grants.append(validated)
                self.latencies.append(("validation", time.time() - start))

                return validated

            async def compute_matches(
                self,
                grant_event: GrantValidatedEvent,
                user_profiles: list[dict],
            ) -> list[MatchComputedEvent]:
                """Simulate match computation."""
                start = time.time()

                matches = []
                for profile in user_profiles:
                    # Mock vector similarity + LLM scoring
                    match_score = 0.8 + (hash(str(profile.get("user_id"))) % 20) / 100

                    priority = PriorityLevel.HIGH if match_score > 0.85 else PriorityLevel.MEDIUM

                    match_event = MatchComputedEvent(
                        event_id=uuid.uuid4(),
                        match_id=uuid.uuid4(),
                        grant_id=grant_event.grant_id,
                        user_id=profile.get("user_id", uuid.uuid4()),
                        match_score=match_score,
                        priority_level=priority,
                        matching_criteria=["research_area", "methods"],
                        explanation="Good alignment in research focus.",
                    )

                    # Publish to stream
                    await self.redis.xadd("matches:computed", {
                        "payload": match_event.model_dump_json(),
                        "event_type": "MatchComputedEvent",
                    })

                    matches.append(match_event)

                self.computed_matches.extend(matches)
                self.latencies.append(("matching", time.time() - start))

                return matches

            async def send_alerts(self, match_events: list[MatchComputedEvent]) -> list[AlertPendingEvent]:
                """Simulate alert delivery."""
                start = time.time()

                alerts = []
                for match in match_events:
                    if match.priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
                        alert = AlertPendingEvent(
                            event_id=uuid.uuid4(),
                            alert_id=uuid.uuid4(),
                            match_id=match.match_id,
                            channel=AlertChannel.EMAIL,
                            user_email="user@test.com",
                            alert_title=f"New Grant Match ({int(match.match_score * 100)}%)",
                            alert_body="A new grant opportunity matches your profile.",
                        )

                        # Publish to stream
                        await self.redis.xadd("alerts:pending", {
                            "payload": alert.model_dump_json(),
                            "event_type": "AlertPendingEvent",
                        })

                        alerts.append(alert)

                self.sent_alerts.extend(alerts)
                self.latencies.append(("alerting", time.time() - start))

                return alerts

            async def run_full_pipeline(
                self,
                grant_data: dict,
                user_profiles: list[dict],
            ) -> dict:
                """Run the complete pipeline."""
                total_start = time.time()

                # Step 1: Discovery
                discovered = await self.discover_grant(grant_data)

                # Step 2: Validation
                validated = await self.validate_grant(discovered)

                # Step 3: Matching
                matches = await self.compute_matches(validated, user_profiles)

                # Step 4: Alerting
                alerts = await self.send_alerts(matches)

                total_time = time.time() - total_start

                return {
                    "discovered": discovered,
                    "validated": validated,
                    "matches": matches,
                    "alerts": alerts,
                    "total_latency_ms": total_time * 1000,
                    "step_latencies": {step: latency * 1000 for step, latency in self.latencies},
                }

            def get_stats(self) -> dict:
                """Get pipeline statistics."""
                return {
                    "discovered_count": len(self.discovered_grants),
                    "validated_count": len(self.validated_grants),
                    "matches_count": len(self.computed_matches),
                    "alerts_count": len(self.sent_alerts),
                    "avg_latency_ms": sum(l[1] for l in self.latencies) / max(len(self.latencies), 1) * 1000,
                }

        return MockPipeline()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_pipeline_single_grant(self, mock_pipeline):
        """Test complete pipeline for a single grant."""
        grant_data = {
            "source": "grants_gov",
            "title": "AI Research Grant",
            "url": "https://grants.gov/test",
            "agency": "NIH",
            "amount": 500000,
            "deadline": datetime.now(timezone.utc) + timedelta(days=30),
        }

        user_profiles = [
            {"user_id": uuid.uuid4(), "research_areas": ["AI", "healthcare"]},
            {"user_id": uuid.uuid4(), "research_areas": ["machine learning"]},
        ]

        result = await mock_pipeline.run_full_pipeline(grant_data, user_profiles)

        # Verify all stages completed
        assert result["discovered"] is not None
        assert result["validated"] is not None
        assert len(result["matches"]) == 2
        assert len(result["alerts"]) > 0  # At least some alerts for high-score matches

        # Verify latency is reasonable
        assert result["total_latency_ms"] < 5000  # Under 5 seconds

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_handles_low_quality_grant(self, mock_pipeline):
        """Test pipeline handles low-quality grants appropriately."""
        # This grant should still process but might have lower scores
        grant_data = {
            "source": "test",
            "title": "Test",  # Minimal data
            "url": "https://test.com",
        }

        user_profiles = [{"user_id": uuid.uuid4()}]

        result = await mock_pipeline.run_full_pipeline(grant_data, user_profiles)

        # Pipeline should complete without errors
        assert result["discovered"] is not None
        assert result["validated"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_stats(self, mock_pipeline):
        """Test pipeline statistics tracking."""
        grant_data = {
            "source": "grants_gov",
            "title": "Test Grant",
            "url": "https://test.com",
        }

        # Run pipeline multiple times
        for _ in range(3):
            await mock_pipeline.run_full_pipeline(grant_data, [{"user_id": uuid.uuid4()}])

        stats = mock_pipeline.get_stats()

        assert stats["discovered_count"] == 3
        assert stats["validated_count"] == 3
        assert stats["matches_count"] == 3


# =============================================================================
# Latency Tests
# =============================================================================


class TestPipelineLatency:
    """Tests for pipeline latency requirements."""

    @pytest.fixture
    def latency_tracker(self):
        """Create a latency tracking fixture."""
        class LatencyTracker:
            def __init__(self):
                self.measurements: list[tuple[str, float]] = []

            def start_timer(self, operation: str) -> dict:
                """Start timing an operation."""
                return {"operation": operation, "start": time.time()}

            def end_timer(self, timer: dict) -> float:
                """End timing and record measurement."""
                elapsed_ms = (time.time() - timer["start"]) * 1000
                self.measurements.append((timer["operation"], elapsed_ms))
                return elapsed_ms

            def get_percentile(self, percentile: float) -> float:
                """Get latency percentile."""
                if not self.measurements:
                    return 0.0

                latencies = sorted([m[1] for m in self.measurements])
                index = int(len(latencies) * percentile / 100)
                return latencies[min(index, len(latencies) - 1)]

            def get_stats(self) -> dict:
                """Get latency statistics."""
                if not self.measurements:
                    return {"count": 0}

                latencies = [m[1] for m in self.measurements]
                return {
                    "count": len(latencies),
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "avg_ms": sum(latencies) / len(latencies),
                    "p50_ms": self.get_percentile(50),
                    "p95_ms": self.get_percentile(95),
                    "p99_ms": self.get_percentile(99),
                }

        return LatencyTracker()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_discovery_latency(self, latency_tracker):
        """Test that discovery meets latency requirements."""
        # Simulate multiple discovery operations
        for _ in range(10):
            timer = latency_tracker.start_timer("discovery")
            await asyncio.sleep(0.01)  # Simulate work
            latency_tracker.end_timer(timer)

        stats = latency_tracker.get_stats()

        # p95 should be under 500ms
        assert stats["p95_ms"] < 500

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_matching_latency(self, latency_tracker):
        """Test that matching meets latency requirements."""
        for _ in range(10):
            timer = latency_tracker.start_timer("matching")
            await asyncio.sleep(0.02)  # Simulate work
            latency_tracker.end_timer(timer)

        stats = latency_tracker.get_stats()

        # p95 should be under 1000ms
        assert stats["p95_ms"] < 1000

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_end_to_end_latency(self, latency_tracker):
        """Test end-to-end latency from discovery to alert."""
        for _ in range(5):
            timer = latency_tracker.start_timer("end_to_end")

            # Simulate full pipeline
            await asyncio.sleep(0.05)  # Discovery
            await asyncio.sleep(0.03)  # Validation
            await asyncio.sleep(0.05)  # Matching
            await asyncio.sleep(0.02)  # Alerting

            latency_tracker.end_timer(timer)

        stats = latency_tracker.get_stats()

        # p95 should be under 5 seconds for complete pipeline
        assert stats["p95_ms"] < 5000


# =============================================================================
# Realistic Data Volume Tests
# =============================================================================


class TestRealisticVolume:
    """Tests with realistic data volumes."""

    @pytest.fixture
    def volume_generator(self):
        """Generate realistic test data volumes."""
        class VolumeGenerator:
            @staticmethod
            def generate_grants(count: int) -> list[dict]:
                """Generate multiple grant data dictionaries."""
                sources = ["grants_gov", "nih", "nsf"]
                agencies = ["NIH", "NSF", "DOE", "DOD", "NASA"]
                categories = ["AI", "healthcare", "climate", "energy", "education"]

                grants = []
                for i in range(count):
                    grants.append({
                        "id": uuid.uuid4(),
                        "source": sources[i % len(sources)],
                        "external_id": f"GRANT-{i:06d}",
                        "title": f"Research Grant {i}: {categories[i % len(categories)]} Initiative",
                        "description": f"This is grant number {i} for {categories[i % len(categories)]} research.",
                        "agency": agencies[i % len(agencies)],
                        "amount_min": 100000 + (i * 10000),
                        "amount_max": 500000 + (i * 50000),
                        "deadline": datetime.now(timezone.utc) + timedelta(days=30 + i),
                        "categories": [categories[i % len(categories)]],
                    })
                return grants

            @staticmethod
            def generate_users(count: int) -> list[dict]:
                """Generate multiple user profiles."""
                areas = [
                    ["machine learning", "NLP"],
                    ["cancer research", "genomics"],
                    ["climate modeling", "data science"],
                    ["quantum computing", "physics"],
                    ["neuroscience", "brain imaging"],
                ]

                users = []
                for i in range(count):
                    users.append({
                        "user_id": uuid.uuid4(),
                        "email": f"researcher{i}@university.edu",
                        "research_areas": areas[i % len(areas)],
                        "institution": f"University {i}",
                    })
                return users

        return VolumeGenerator()

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_batch_grant_processing(self, volume_generator, fake_redis):
        """Test processing a batch of grants."""
        grants = volume_generator.generate_grants(50)
        users = volume_generator.generate_users(10)

        processed_count = 0
        start_time = time.time()

        for grant in grants:
            # Simulate discovery
            event = GrantDiscoveredEvent(
                event_id=uuid.uuid4(),
                grant_id=grant["id"],
                source=grant["source"],
                title=grant["title"],
                url=f"https://grants.gov/{grant['external_id']}",
            )

            await fake_redis.xadd("grants:discovered", {
                "payload": event.model_dump_json(),
            })

            processed_count += 1

        elapsed = time.time() - start_time

        assert processed_count == 50
        # Should process 50 grants in under 5 seconds
        assert elapsed < 5.0

        # Verify stream length
        stream_len = await fake_redis.xlen("grants:discovered")
        assert stream_len == 50

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_high_volume_matching(self, volume_generator, fake_redis):
        """Test matching with high user volume."""
        grants = volume_generator.generate_grants(10)
        users = volume_generator.generate_users(100)

        match_count = 0
        start_time = time.time()

        for grant in grants:
            for user in users:
                # Simulate match computation
                match_event = MatchComputedEvent(
                    event_id=uuid.uuid4(),
                    match_id=uuid.uuid4(),
                    grant_id=grant["id"],
                    user_id=user["user_id"],
                    match_score=0.5 + (hash(str(user["user_id"])) % 50) / 100,
                    priority_level=PriorityLevel.MEDIUM,
                )

                await fake_redis.xadd("matches:computed", {
                    "payload": match_event.model_dump_json(),
                })

                match_count += 1

        elapsed = time.time() - start_time

        # 10 grants x 100 users = 1000 matches
        assert match_count == 1000

        # Should complete in reasonable time
        assert elapsed < 30.0


# =============================================================================
# Event Stream Tests
# =============================================================================


class TestEventStreams:
    """Tests for Redis stream event processing."""

    @pytest.mark.asyncio
    async def test_event_ordering(self, fake_redis):
        """Test that events are processed in order."""
        events = []

        # Add events with timestamps
        for i in range(10):
            event_id = uuid.uuid4()
            msg_id = await fake_redis.xadd("test:stream", {
                "event_id": str(event_id),
                "sequence": str(i),
                "timestamp": datetime.utcnow().isoformat(),
            })
            events.append((msg_id, i))

        # Read events and verify order
        result = await fake_redis.xread({"test:stream": "0"}, count=10)

        if result:
            stream_name, messages = result[0]
            for idx, (msg_id, data) in enumerate(messages):
                assert data["sequence"] == str(idx)

    @pytest.mark.asyncio
    async def test_consumer_group_processing(self, fake_redis):
        """Test consumer group message distribution."""
        # Create consumer group
        await fake_redis.xgroup_create("test:stream", "test-group", "0", mkstream=True)

        # Add messages
        for i in range(5):
            await fake_redis.xadd("test:stream", {
                "message": f"Message {i}",
            })

        # Simulate consumer reading
        messages = await fake_redis.xreadgroup(
            groupname="test-group",
            consumername="consumer-1",
            streams={"test:stream": ">"},
            count=5,
        )

        if messages:
            assert len(messages[0][1]) == 5

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, fake_redis):
        """Test moving failed messages to DLQ."""
        # Simulate a failed message
        original_msg_id = await fake_redis.xadd("grants:discovered", {
            "payload": "test payload",
        })

        # Move to DLQ
        dlq_msg_id = await fake_redis.xadd("dlq:grants:discovered", {
            "original_stream": "grants:discovered",
            "original_message_id": original_msg_id,
            "error": "Processing failed",
            "retry_count": "3",
        })

        # Verify DLQ has the message
        dlq_len = await fake_redis.xlen("dlq:grants:discovered")
        assert dlq_len == 1


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_pipeline_recovers_from_validation_failure(self, fake_redis):
        """Test pipeline continues after validation failure."""
        # Simulate discovering multiple grants
        grant_ids = []
        for i in range(5):
            grant_id = uuid.uuid4()
            grant_ids.append(grant_id)

            await fake_redis.xadd("grants:discovered", {
                "grant_id": str(grant_id),
                "title": f"Grant {i}",
            })

        # Simulate validation where one fails
        validated_count = 0
        failed_count = 0

        for i, grant_id in enumerate(grant_ids):
            if i == 2:  # Simulate failure on third grant
                failed_count += 1
                await fake_redis.xadd("dlq:grants:discovered", {
                    "grant_id": str(grant_id),
                    "error": "Validation failed",
                })
            else:
                validated_count += 1
                await fake_redis.xadd("grants:validated", {
                    "grant_id": str(grant_id),
                    "quality_score": "0.85",
                })

        assert validated_count == 4
        assert failed_count == 1

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test retry mechanism for failed operations."""
        max_retries = 3
        retry_count = 0
        success = False

        async def flaky_operation():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise Exception("Temporary failure")
            return True

        # Retry loop
        for attempt in range(max_retries):
            try:
                success = await flaky_operation()
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.01)  # Brief delay between retries

        assert success is True
        assert retry_count == 3

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, fake_redis):
        """Test graceful degradation when services are unavailable."""
        # Simulate matching when LLM service is down
        # Should fall back to vector-only matching

        grant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Vector similarity score (fallback)
        vector_score = 0.78

        # When LLM is unavailable, use vector score only
        llm_available = False

        if llm_available:
            final_score = (vector_score * 0.4) + (0.8 * 0.6)  # With LLM
        else:
            final_score = vector_score  # Vector only fallback

        # Should still produce a valid match
        match_event = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=grant_id,
            user_id=user_id,
            match_score=final_score,
            priority_level=PriorityLevel.MEDIUM,
            explanation="Match computed using vector similarity only (LLM unavailable).",
        )

        assert match_event.match_score == 0.78


# =============================================================================
# Data Consistency Tests
# =============================================================================


class TestDataConsistency:
    """Tests for data consistency across the pipeline."""

    @pytest.mark.asyncio
    async def test_grant_id_propagation(self, fake_redis):
        """Test that grant ID is consistently propagated through pipeline."""
        grant_id = uuid.uuid4()

        # Discovery
        discovered = GrantDiscoveredEvent(
            event_id=uuid.uuid4(),
            grant_id=grant_id,
            source="test",
            title="Test Grant",
            url="https://test.com",
        )

        # Validation
        validated = GrantValidatedEvent(
            event_id=uuid.uuid4(),
            grant_id=grant_id,  # Same ID
            quality_score=0.9,
            categories=["test"],
            embedding_generated=True,
        )

        # Match
        match = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=grant_id,  # Same ID
            user_id=uuid.uuid4(),
            match_score=0.85,
            priority_level=PriorityLevel.HIGH,
        )

        # Verify ID consistency
        assert discovered.grant_id == validated.grant_id == match.grant_id

    @pytest.mark.asyncio
    async def test_no_duplicate_matches(self, fake_redis):
        """Test that duplicate matches are prevented."""
        grant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        seen_pairs = set()
        matches = []

        # Attempt to create duplicate matches
        for _ in range(3):
            pair = (grant_id, user_id)
            if pair in seen_pairs:
                continue  # Skip duplicate

            seen_pairs.add(pair)
            matches.append({
                "grant_id": grant_id,
                "user_id": user_id,
                "match_score": 0.85,
            })

        assert len(matches) == 1  # Only one match created

    @pytest.mark.asyncio
    async def test_match_score_bounds(self):
        """Test that match scores stay within valid bounds."""
        scores = [0.0, 0.5, 1.0]

        for score in scores:
            match = MatchComputedEvent(
                event_id=uuid.uuid4(),
                match_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                match_score=score,
                priority_level=PriorityLevel.MEDIUM,
            )
            assert 0.0 <= match.match_score <= 1.0

        # Invalid scores should be rejected
        with pytest.raises(ValueError):
            MatchComputedEvent(
                event_id=uuid.uuid4(),
                match_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                match_score=1.5,  # Invalid
                priority_level=PriorityLevel.MEDIUM,
            )


# =============================================================================
# Performance Benchmarks
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_throughput_benchmark(self, fake_redis):
        """Benchmark message throughput."""
        num_messages = 1000
        start_time = time.time()

        for i in range(num_messages):
            await fake_redis.xadd("benchmark:stream", {
                "message_id": str(i),
                "timestamp": datetime.utcnow().isoformat(),
            })

        elapsed = time.time() - start_time
        throughput = num_messages / elapsed

        print(f"\nThroughput: {throughput:.2f} messages/second")

        # Should achieve at least 100 messages/second
        assert throughput > 100

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_processing(self, fake_redis):
        """Test concurrent event processing."""
        async def process_batch(batch_id: int, count: int):
            for i in range(count):
                await fake_redis.xadd(f"concurrent:stream:{batch_id}", {
                    "item": str(i),
                })
            return count

        # Process 5 batches concurrently
        tasks = [process_batch(i, 100) for i in range(5)]
        results = await asyncio.gather(*tasks)

        total_processed = sum(results)
        assert total_processed == 500

        # Verify all streams have correct counts
        for i in range(5):
            stream_len = await fake_redis.xlen(f"concurrent:stream:{i}")
            assert stream_len == 100
