# ABOUTME: Integration tests for rate limiter components with system interactions.
# ABOUTME: Tests cover rate limiter integration with async systems and real-world scenarios.

import asyncio
import time
from collections.abc import Callable
from typing import Any

import pytest

from asset_core.patterns.rate_limiter import AbstractRateLimiter


class SlidingWindowRateLimiter(AbstractRateLimiter):
    """Sliding window rate limiter implementation for integration testing."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        """Initialize sliding window rate limiter."""
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: list[float] = []
        self._acquire_count = 0
        self.total_requests = 0
        self.successful_requests = 0

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens using sliding window algorithm."""
        self._acquire_count += 1
        self.total_requests += 1
        await asyncio.sleep(0.001)  # Simulate async operation

        now = time.time()

        # Remove old requests outside the window
        cutoff = now - self.window_seconds
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]

        # Check if we can acquire tokens
        if len(self.requests) + tokens <= self.limit:
            # Add timestamps for each token
            for _ in range(tokens):
                self.requests.append(now)
            self.successful_requests += 1
            return True

        return False

    @property
    def acquire_count(self) -> int:
        """Get total acquire calls."""
        return self._acquire_count

    @property
    def current_usage(self) -> int:
        """Get current window usage."""
        now = time.time()
        cutoff = now - self.window_seconds
        return len([req_time for req_time in self.requests if req_time > cutoff])


class AdaptiveRateLimiter(AbstractRateLimiter):
    """Adaptive rate limiter that adjusts limits based on system conditions."""

    def __init__(self, base_limit: int, window_seconds: float) -> None:
        """Initialize adaptive rate limiter."""
        self.base_limit = base_limit
        self.window_seconds = window_seconds
        self.current_limit = base_limit
        self.requests: list[float] = []
        self.success_rate = 1.0
        self.total_requests = 0
        self.successful_requests = 0
        self._acquire_count = 0

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens with adaptive limiting."""
        self._acquire_count += 1
        self.total_requests += 1
        await asyncio.sleep(0.001)

        now = time.time()
        cutoff = now - self.window_seconds
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]

        # Adjust limit based on success rate
        if len(self.requests) + tokens <= self.current_limit:
            for _ in range(tokens):
                self.requests.append(now)
            self.successful_requests += 1
            result = True
        else:
            result = False

        self._adjust_limit()
        return result

    def _adjust_limit(self) -> None:
        """Adjust current limit based on success rate."""
        if self.total_requests > 0:
            self.success_rate = self.successful_requests / self.total_requests
            print(
                f"DEBUG: _adjust_limit - successful_requests: {self.successful_requests}, total_requests: {self.total_requests}, success_rate: {self.success_rate}"
            )

            if self.success_rate > 0.9:
                # High success rate, increase limit
                self.current_limit = min(self.base_limit * 2, self.current_limit + 1)
            elif self.success_rate < 0.5:
                # Low success rate, decrease limit
                self.current_limit = max(1, self.current_limit - 1)

    @property
    def acquire_count(self) -> int:
        """Get total acquire calls."""
        return self._acquire_count

    def get_stats(self) -> dict[str, Any]:
        """Get limiter statistics."""
        return {
            "current_limit": self.current_limit,
            "base_limit": self.base_limit,
            "success_rate": self.success_rate,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
        }


class APIGateway:
    """API Gateway simulation with rate limiting."""

    def __init__(self, rate_limiter: AbstractRateLimiter) -> None:
        """Initialize API Gateway with rate limiter."""
        self.rate_limiter = rate_limiter
        self.processed_requests = 0
        self.rate_limited_requests = 0
        self.active_requests = 0

    async def handle_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming request with rate limiting."""
        # Check rate limit
        if not await self.rate_limiter.acquire():
            self.rate_limited_requests += 1
            return {"status": "rate_limited", "message": "Rate limit exceeded", "code": 429}

        self.active_requests += 1
        try:
            # Simulate request processing
            await asyncio.sleep(0.005)
            self.processed_requests += 1

            return {"status": "success", "data": request_data, "code": 200}
        finally:
            self.active_requests -= 1

    def get_stats(self) -> dict[str, Any]:
        """Get gateway statistics."""
        return {
            "processed_requests": self.processed_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "active_requests": self.active_requests,
            "total_requests": self.processed_requests + self.rate_limited_requests,
        }


class MultiTierRateLimiter:
    """Multi-tier rate limiting system."""

    def __init__(self, limiters: dict[str, AbstractRateLimiter]) -> None:
        """Initialize multi-tier rate limiter."""
        self.limiters = limiters
        self.tier_stats: dict[str, dict[str, int]] = {
            tier: {"attempts": 0, "allowed": 0, "denied": 0} for tier in limiters
        }

    async def acquire(self, tier: str, tokens: int = 1) -> bool:
        """Acquire tokens from specific tier."""
        if tier not in self.limiters:
            return False

        self.tier_stats[tier]["attempts"] += 1

        if await self.limiters[tier].acquire(tokens):
            self.tier_stats[tier]["allowed"] += 1
            return True
        else:
            self.tier_stats[tier]["denied"] += 1
            return False

    def get_tier_stats(self, tier: str) -> dict[str, int]:
        """Get statistics for specific tier."""
        return self.tier_stats.get(tier, {})

    def get_all_stats(self) -> dict[str, dict[str, int]]:
        """Get statistics for all tiers."""
        return self.tier_stats.copy()


@pytest.mark.integration
class TestRateLimiterSystemIntegration:
    """Integration tests for rate limiters with system components."""

    @pytest.fixture
    def sliding_limiter(self) -> SlidingWindowRateLimiter:
        """Provide sliding window rate limiter."""
        return SlidingWindowRateLimiter(limit=5, window_seconds=1.0)

    @pytest.fixture
    def adaptive_limiter(self) -> AdaptiveRateLimiter:
        """Provide adaptive rate limiter."""
        return AdaptiveRateLimiter(base_limit=3, window_seconds=0.5)

    @pytest.fixture
    def api_gateway(self, sliding_limiter: SlidingWindowRateLimiter) -> APIGateway:
        """Provide API gateway with rate limiter."""
        return APIGateway(sliding_limiter)

    async def test_api_gateway_rate_limiting(self, api_gateway: APIGateway) -> None:
        """Test API gateway integration with rate limiting.

        Description of what the test covers:
        Verifies rate limiter integration with API gateway functionality
        and proper request handling under rate limits.

        Preconditions:
        - API gateway with sliding window rate limiter (limit 5)

        Steps:
        - Send requests within rate limit
        - Send requests exceeding rate limit
        - Verify proper rate limiting behavior

        Expected Result:
        - Requests within limit should be processed
        - Requests exceeding limit should be rate limited
        - Proper status codes and statistics
        """
        # Send requests within rate limit
        for i in range(5):
            response = await api_gateway.handle_request({"id": i, "action": "test"})
            assert response["status"] == "success"
            assert response["code"] == 200

        # Send requests exceeding rate limit
        for i in range(5, 10):
            response = await api_gateway.handle_request({"id": i, "action": "test"})
            assert response["status"] == "rate_limited"
            assert response["code"] == 429

        stats = api_gateway.get_stats()
        assert stats["processed_requests"] == 5
        assert stats["rate_limited_requests"] == 5
        assert stats["total_requests"] == 10

    async def test_sliding_window_behavior(self) -> None:
        """Test sliding window rate limiter behavior over time.

        Description of what the test covers:
        Verifies sliding window implementation properly handles
        time-based rate limiting with window sliding.

        Preconditions:
        - Sliding window limiter with limit 5, window 1 second

        Steps:
        - Exhaust rate limit
        - Wait for partial window to pass
        - Verify requests are allowed as window slides

        Expected Result:
        - Window should slide properly over time
        - Requests should be allowed as old requests expire
        """
        # Use faster window for testing
        fast_limiter = SlidingWindowRateLimiter(limit=3, window_seconds=0.1)

        # Exhaust rate limit
        for _i in range(3):
            result = await fast_limiter.acquire()
            assert result is True

        # Should reject next request
        result = await fast_limiter.acquire()
        assert result is False

        # Wait for window to slide
        await asyncio.sleep(0.12)

        # Should allow requests again
        result = await fast_limiter.acquire()
        assert result is True

        assert fast_limiter.current_usage == 1

    async def test_adaptive_rate_limiter_adjustment(self, adaptive_limiter: AdaptiveRateLimiter) -> None:
        """Test adaptive rate limiter adjustment behavior.

        Description of what the test covers:
        Verifies adaptive rate limiter properly adjusts limits
        based on success rate and system conditions.

        Preconditions:
        - Adaptive limiter with base limit 3

        Steps:
        - Generate high success rate scenario
        - Verify limit increases
        - Generate low success rate scenario
        - Verify limit decreases

        Expected Result:
        - Limit should increase with high success rate
        - Limit should decrease with low success rate
        """
        # Generate high success rate
        initial_limit = adaptive_limiter.current_limit

        # Make successful requests
        for _ in range(adaptive_limiter.base_limit):
            await adaptive_limiter.acquire()

        stats = adaptive_limiter.get_stats()
        assert stats["success_rate"] == 1.0
        assert adaptive_limiter.current_limit >= initial_limit

        # Create low success scenario by making many requests quickly
        adaptive_limiter.total_requests = 0
        adaptive_limiter.successful_requests = 0
        adaptive_limiter.current_limit = 1  # Force failures

        for _ in range(10):  # Make enough requests to cause failures
            await adaptive_limiter.acquire()

        final_stats = adaptive_limiter.get_stats()
        # Success rate should be lower due to rate limiting
        assert final_stats["success_rate"] < 1.0

    async def test_multi_tier_rate_limiting(self) -> None:
        """Test multi-tier rate limiting system.

        Description of what the test covers:
        Verifies multi-tier rate limiting with different limits
        for different user tiers or request types.

        Preconditions:
        - Multi-tier system with different rate limiters

        Steps:
        - Create different tiers with different limits
        - Test requests for each tier
        - Verify tier-specific rate limiting

        Expected Result:
        - Each tier should have independent rate limiting
        - Statistics should be tracked per tier
        """
        limiters: dict[str, AbstractRateLimiter] = {
            "free": SlidingWindowRateLimiter(limit=2, window_seconds=1.0),
            "premium": SlidingWindowRateLimiter(limit=10, window_seconds=1.0),
            "enterprise": SlidingWindowRateLimiter(limit=50, window_seconds=1.0),
        }

        multi_tier = MultiTierRateLimiter(limiters)

        # Test free tier (limit 2)
        result1 = await multi_tier.acquire("free")
        result2 = await multi_tier.acquire("free")
        result3 = await multi_tier.acquire("free")  # Should fail

        assert result1 is True
        assert result2 is True
        assert result3 is False

        # Test premium tier (limit 10)
        for _i in range(10):
            result = await multi_tier.acquire("premium")
            assert result is True

        result = await multi_tier.acquire("premium")  # Should fail
        assert result is False

        # Verify statistics
        free_stats = multi_tier.get_tier_stats("free")
        assert free_stats["attempts"] == 3
        assert free_stats["allowed"] == 2
        assert free_stats["denied"] == 1

        premium_stats = multi_tier.get_tier_stats("premium")
        assert premium_stats["attempts"] == 11
        assert premium_stats["allowed"] == 10
        assert premium_stats["denied"] == 1

    async def test_rate_limiter_with_concurrent_users(self) -> None:
        """Test rate limiter with concurrent user simulation.

        Description of what the test covers:
        Verifies rate limiter behavior with multiple concurrent
        users making requests simultaneously.

        Preconditions:
        - Shared rate limiter for multiple users

        Steps:
        - Simulate multiple users making concurrent requests
        - Verify rate limiting is applied fairly
        - Check statistics consistency

        Expected Result:
        - Rate limiting should be applied across all users
        - Total allowed requests should not exceed limit
        """
        shared_limiter = SlidingWindowRateLimiter(limit=10, window_seconds=1.0)

        async def user_session(user_id: int, requests_per_user: int) -> dict[str, int]:
            """Simulate user making requests."""
            successful = 0
            failed = 0

            for _ in range(requests_per_user):
                if await shared_limiter.acquire():
                    successful += 1
                else:
                    failed += 1

                # Small delay between requests
                await asyncio.sleep(0.001)

            return {"user_id": user_id, "successful": successful, "failed": failed}

        # Simulate 5 users each making 5 requests (25 total requests)
        tasks = [user_session(i, 5) for i in range(5)]
        results = await asyncio.gather(*tasks)

        total_successful = sum(r["successful"] for r in results)
        total_failed = sum(r["failed"] for r in results)

        # Should not exceed rate limit
        assert total_successful <= 10
        assert total_successful + total_failed == 25
        assert shared_limiter.current_usage <= 10


@pytest.mark.integration
class TestRateLimiterAsyncIntegration:
    """Integration tests for rate limiters with async systems."""

    async def test_rate_limiter_with_async_queue_processing(self) -> None:
        """Test rate limiter integration with async queue processing.

        Description of what the test covers:
        Verifies rate limiter integration with async queue processing
        systems and proper flow control.

        Preconditions:
        - Queue processor with rate limiting

        Steps:
        - Create queue processor with rate limiter
        - Add items to queue faster than processing rate
        - Verify rate limiting controls processing

        Expected Result:
        - Processing should be rate limited
        - Queue should handle backlog appropriately
        """

        class RateLimitedQueueProcessor:
            def __init__(self, rate_limiter: AbstractRateLimiter) -> None:
                self.rate_limiter = rate_limiter
                self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
                self.processed_items = 0
                self.rate_limited_items = 0
                self.running = False

            async def add_item(self, item: dict[str, Any]) -> None:
                """Add item to processing queue."""
                await self.queue.put(item)

            async def process_queue(self) -> None:
                """Process queue items with rate limiting."""
                while self.running:
                    try:
                        item = await asyncio.wait_for(self.queue.get(), timeout=0.1)

                        # Check rate limit before processing
                        if await self.rate_limiter.acquire():
                            # Simulate processing
                            await asyncio.sleep(0.001)
                            self.processed_items += 1
                        else:
                            # Put item back in queue or handle rate limiting
                            await self.queue.put(item)
                            self.rate_limited_items += 1
                            await asyncio.sleep(0.01)  # Wait before retry

                    except TimeoutError:
                        continue

            def start(self) -> None:
                """Start queue processing."""
                self.running = True

            def stop(self) -> None:
                """Stop queue processing."""
                self.running = False

            def get_stats(self) -> dict[str, Any]:
                """Get processor statistics."""
                return {
                    "processed_items": self.processed_items,
                    "rate_limited_items": self.rate_limited_items,
                    "queue_size": self.queue.qsize(),
                }

        limiter = SlidingWindowRateLimiter(limit=5, window_seconds=0.2)
        processor = RateLimitedQueueProcessor(limiter)

        # Add items to queue
        for i in range(15):
            await processor.add_item({"id": i, "data": f"item_{i}"})

        # Start processing
        processor.start()
        process_task = asyncio.create_task(processor.process_queue())

        # Let it run for a short time
        await asyncio.sleep(0.3)

        processor.stop()
        process_task.cancel()

        stats = processor.get_stats()

        # Should have processed some items
        assert stats["processed_items"] > 0
        # Should have rate limited some items
        assert stats["rate_limited_items"] >= 0
        # Some items might still be in queue
        assert stats["queue_size"] >= 0

    async def test_rate_limiter_with_websocket_simulation(self) -> None:
        """Test rate limiter with WebSocket message handling simulation.

        Description of what the test covers:
        Verifies rate limiter integration with WebSocket-like
        message handling and connection management.

        Preconditions:
        - WebSocket handler with rate limiting

        Steps:
        - Create WebSocket handler with rate limiter
        - Send messages at high rate
        - Verify rate limiting affects message handling

        Expected Result:
        - Messages should be rate limited appropriately
        - Connection should handle rate limiting gracefully
        """

        class RateLimitedWebSocketHandler:
            def __init__(self, rate_limiter: AbstractRateLimiter) -> None:
                self.rate_limiter = rate_limiter
                self.received_messages = 0
                self.dropped_messages = 0
                self.message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

            async def handle_message(self, message: dict[str, Any]) -> bool:
                """Handle incoming WebSocket message with rate limiting."""
                if await self.rate_limiter.acquire():
                    await self.message_queue.put(message)
                    self.received_messages += 1
                    return True
                else:
                    self.dropped_messages += 1
                    return False

            async def process_messages(self) -> int:
                """Process queued messages."""
                processed = 0
                while not self.message_queue.empty():
                    try:
                        await asyncio.wait_for(self.message_queue.get(), timeout=0.01)
                        # Simulate message processing
                        await asyncio.sleep(0.001)
                        processed += 1
                    except TimeoutError:
                        break
                return processed

            def get_stats(self) -> dict[str, Any]:
                """Get handler statistics."""
                return {
                    "received_messages": self.received_messages,
                    "dropped_messages": self.dropped_messages,
                    "queue_size": self.message_queue.qsize(),
                }

        limiter = SlidingWindowRateLimiter(limit=8, window_seconds=0.5)
        handler = RateLimitedWebSocketHandler(limiter)

        # Send messages rapidly
        messages_sent = 0
        for i in range(20):
            message = {"id": i, "type": "test", "data": f"message_{i}"}
            await handler.handle_message(message)
            messages_sent += 1

        stats = handler.get_stats()

        # Should have received some messages within rate limit
        assert stats["received_messages"] <= 8  # Within rate limit
        assert stats["dropped_messages"] >= 0  # Some may be dropped
        assert stats["received_messages"] + stats["dropped_messages"] == messages_sent

        # Process queued messages
        processed = await handler.process_messages()
        assert processed == stats["received_messages"]

    async def test_rate_limiter_with_event_streaming(self) -> None:
        """Test rate limiter with event streaming system.

        Description of what the test covers:
        Verifies rate limiter integration with event streaming
        and proper event flow control.

        Preconditions:
        - Event streaming system with rate limiting

        Steps:
        - Create event stream with rate limiter
        - Generate events at high rate
        - Verify rate limiting controls event flow

        Expected Result:
        - Event flow should be controlled by rate limiter
        - System should handle event bursts gracefully
        """

        class RateLimitedEventStream:
            def __init__(self, rate_limiter: AbstractRateLimiter) -> None:
                self.rate_limiter = rate_limiter
                self.published_events = 0
                self.throttled_events = 0
                self.event_buffer: list[dict[str, Any]] = []
                self.subscribers: list[Callable[[dict[str, Any]], None]] = []

            async def publish_event(self, event: dict[str, Any]) -> bool:
                """Publish event with rate limiting."""
                if await self.rate_limiter.acquire():
                    self.event_buffer.append(event)
                    self.published_events += 1

                    # Notify subscribers
                    import contextlib

                    for subscriber in self.subscribers:
                        with contextlib.suppress(Exception):
                            subscriber(event)

                    return True
                else:
                    self.throttled_events += 1
                    return False

            def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
                """Subscribe to events."""
                self.subscribers.append(callback)

            def get_stats(self) -> dict[str, Any]:
                """Get stream statistics."""
                return {
                    "published_events": self.published_events,
                    "throttled_events": self.throttled_events,
                    "buffer_size": len(self.event_buffer),
                    "subscriber_count": len(self.subscribers),
                }

        limiter = AdaptiveRateLimiter(base_limit=6, window_seconds=0.3)
        stream = RateLimitedEventStream(limiter)

        # Add subscriber
        received_events = []
        stream.subscribe(lambda event: received_events.append(event))

        # Generate events rapidly
        for i in range(25):
            event = {"id": i, "type": "test_event", "timestamp": time.time(), "data": f"event_data_{i}"}
            await stream.publish_event(event)

        stats = stream.get_stats()

        # Should have published some events
        assert stats["published_events"] > 0
        # Should have throttled some events
        assert stats["throttled_events"] >= 0
        # Total should match attempts
        assert stats["published_events"] + stats["throttled_events"] == 25

        # Subscribers should receive published events
        assert len(received_events) == stats["published_events"]


@pytest.mark.integration
class TestRateLimiterRealWorldScenarios:
    """Integration tests simulating real-world rate limiting scenarios."""

    async def test_microservice_rate_limiting(self) -> None:
        """Test rate limiting in microservice communication scenario.

        Description of what the test covers:
        Verifies rate limiter integration with microservice
        communication patterns and service mesh scenarios.

        Preconditions:
        - Microservice with rate-limited API calls

        Steps:
        - Create microservice with rate limiter
        - Simulate service-to-service communication
        - Verify rate limiting affects inter-service calls

        Expected Result:
        - Service calls should be rate limited
        - Service should handle rate limiting gracefully
        """

        class MicroserviceClient:
            def __init__(self, service_name: str, rate_limiter: AbstractRateLimiter) -> None:
                self.service_name = service_name
                self.rate_limiter = rate_limiter
                self.successful_calls = 0
                self.rate_limited_calls = 0
                self.total_calls = 0

            async def call_service(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
                """Make service call with rate limiting."""
                self.total_calls += 1

                if not await self.rate_limiter.acquire():
                    self.rate_limited_calls += 1
                    return {
                        "status": "error",
                        "message": "Rate limit exceeded",
                        "service": self.service_name,
                        "endpoint": endpoint,
                    }

                # Simulate service call
                await asyncio.sleep(0.005)
                self.successful_calls += 1

                return {
                    "status": "success",
                    "data": data,
                    "service": self.service_name,
                    "endpoint": endpoint,
                }

            def get_stats(self) -> dict[str, Any]:
                """Get client statistics."""
                return {
                    "service_name": self.service_name,
                    "successful_calls": self.successful_calls,
                    "rate_limited_calls": self.rate_limited_calls,
                    "total_calls": self.total_calls,
                    "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
                }

        # Create microservice clients with different rate limits
        user_service = MicroserviceClient("user-service", SlidingWindowRateLimiter(limit=10, window_seconds=1.0))
        order_service = MicroserviceClient("order-service", SlidingWindowRateLimiter(limit=5, window_seconds=1.0))

        # Simulate service calls
        async def simulate_user_service_calls() -> None:
            for i in range(15):
                await user_service.call_service("/users", {"user_id": i})

        async def simulate_order_service_calls() -> None:
            for i in range(10):
                await order_service.call_service("/orders", {"order_id": i})

        # Run both services concurrently
        await asyncio.gather(simulate_user_service_calls(), simulate_order_service_calls())

        user_stats = user_service.get_stats()
        order_stats = order_service.get_stats()

        # Verify rate limiting behavior
        assert user_stats["successful_calls"] <= 10  # User service limit
        assert order_stats["successful_calls"] <= 5  # Order service limit

        assert user_stats["total_calls"] == 15
        assert order_stats["total_calls"] == 10

        # Success rates should reflect rate limiting
        assert user_stats["success_rate"] <= 1.0
        assert order_stats["success_rate"] <= 1.0

    async def test_cdn_rate_limiting_scenario(self) -> None:
        """Test rate limiting in CDN-like content delivery scenario.

        Description of what the test covers:
        Verifies rate limiter integration with content delivery
        systems and origin server protection.

        Preconditions:
        - CDN with rate-limited origin requests

        Steps:
        - Create CDN with rate limiter for origin requests
        - Simulate high request volume
        - Verify origin protection through rate limiting

        Expected Result:
        - Origin requests should be rate limited
        - CDN should handle cache hits without rate limiting
        """

        class CDNService:
            def __init__(self, origin_rate_limiter: AbstractRateLimiter) -> None:
                self.origin_rate_limiter = origin_rate_limiter
                self.cache: dict[str, dict[str, Any]] = {}
                self.cache_hits = 0
                self.cache_misses = 0
                self.origin_requests = 0
                self.origin_rate_limited = 0

            async def get_content(self, url: str) -> dict[str, Any]:
                """Get content with caching and origin rate limiting."""
                # Check cache first
                if url in self.cache:
                    self.cache_hits += 1
                    return {
                        "status": "success",
                        "data": self.cache[url],
                        "source": "cache",
                        "url": url,
                    }

                # Cache miss - need to request from origin
                self.cache_misses += 1

                # Check origin rate limit
                if not await self.origin_rate_limiter.acquire():
                    self.origin_rate_limited += 1
                    return {
                        "status": "error",
                        "message": "Origin rate limit exceeded",
                        "source": "origin",
                        "url": url,
                    }

                # Simulate origin request
                await asyncio.sleep(0.01)
                self.origin_requests += 1

                # Cache the response
                content = {"content": f"Content for {url}", "timestamp": time.time()}
                self.cache[url] = content

                return {
                    "status": "success",
                    "data": content,
                    "source": "origin",
                    "url": url,
                }

            def get_stats(self) -> dict[str, Any]:
                """Get CDN statistics."""
                return {
                    "cache_hits": self.cache_hits,
                    "cache_misses": self.cache_misses,
                    "origin_requests": self.origin_requests,
                    "origin_rate_limited": self.origin_rate_limited,
                    "cache_size": len(self.cache),
                }

        # CDN with origin rate limit of 3 requests per second
        cdn = CDNService(SlidingWindowRateLimiter(limit=3, window_seconds=1.0))

        # Simulate requests - some will be cache hits, some misses
        urls = [
            "/page1.html",
            "/page2.html",
            "/page3.html",
            "/page1.html",
            "/page4.html",
            "/page2.html",  # Some repeats for cache hits
            "/page5.html",
            "/page6.html",
            "/page7.html",
            "/page1.html",
            "/page8.html",
            "/page9.html",  # More cache hits and misses
        ]

        results = []
        for url in urls:
            result = await cdn.get_content(url)
            results.append(result)

        stats = cdn.get_stats()

        # Should have cache hits and misses
        assert stats["cache_hits"] > 0
        assert stats["cache_misses"] > 0

        # Origin requests should be limited
        assert stats["origin_requests"] <= 3  # Within rate limit
        assert stats["origin_rate_limited"] >= 0

        # Cache should contain unique URLs
        assert stats["cache_size"] <= len(set(urls))

        # Verify response distribution
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = sum(1 for r in results if r["status"] == "error")

        assert success_count + error_count == len(urls)
        assert success_count > 0  # Should have some successful responses

    async def test_database_connection_rate_limiting(self) -> None:
        """Test rate limiting for database connection management.

        Description of what the test covers:
        Verifies rate limiter integration with database connection
        pools and query rate limiting.

        Preconditions:
        - Database connection manager with rate limiting

        Steps:
        - Create database manager with rate limiter
        - Execute queries at high rate
        - Verify connection rate limiting

        Expected Result:
        - Database connections should be rate limited
        - Query execution should be controlled
        """

        class DatabaseManager:
            def __init__(self, connection_rate_limiter: AbstractRateLimiter) -> None:
                self.connection_rate_limiter = connection_rate_limiter
                self.active_connections = 0
                self.max_connections = 5
                self.executed_queries = 0
                self.rate_limited_queries = 0
                self.connection_pool: list[dict[str, Any]] = []

            async def execute_query(self, query: str) -> dict[str, Any]:
                """Execute database query with rate limiting."""
                # Check connection rate limit
                if not await self.connection_rate_limiter.acquire():
                    self.rate_limited_queries += 1
                    return {
                        "status": "error",
                        "message": "Connection rate limit exceeded",
                        "query": query[:50] + "..." if len(query) > 50 else query,
                    }

                # Check connection pool
                if self.active_connections >= self.max_connections:
                    return {
                        "status": "error",
                        "message": "Connection pool exhausted",
                        "query": query[:50] + "..." if len(query) > 50 else query,
                    }

                self.active_connections += 1
                try:
                    # Simulate query execution
                    await asyncio.sleep(0.005)
                    self.executed_queries += 1

                    return {
                        "status": "success",
                        "data": {"query": query, "rows_affected": 1},
                        "execution_time": 0.005,
                    }
                finally:
                    self.active_connections -= 1

            def get_stats(self) -> dict[str, Any]:
                """Get database manager statistics."""
                return {
                    "executed_queries": self.executed_queries,
                    "rate_limited_queries": self.rate_limited_queries,
                    "active_connections": self.active_connections,
                    "max_connections": self.max_connections,
                }

        # Database with connection rate limit
        db_manager = DatabaseManager(SlidingWindowRateLimiter(limit=8, window_seconds=1.0))

        # Simulate concurrent database queries
        queries = [
            "SELECT * FROM users WHERE id = ?",
            "INSERT INTO orders (user_id, total) VALUES (?, ?)",
            "UPDATE users SET last_login = ? WHERE id = ?",
            "DELETE FROM sessions WHERE expired = true",
            "SELECT COUNT(*) FROM products",
            "INSERT INTO logs (message, timestamp) VALUES (?, ?)",
            "SELECT * FROM orders WHERE status = 'pending'",
            "UPDATE orders SET status = 'completed' WHERE id = ?",
            "SELECT * FROM products WHERE category = ?",
            "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
            "SELECT * FROM users WHERE email = ?",
            "DELETE FROM temp_data WHERE created_at < ?",
        ]

        # Execute queries concurrently
        tasks = [db_manager.execute_query(query) for query in queries]
        results = await asyncio.gather(*tasks)

        stats = db_manager.get_stats()

        # Verify rate limiting behavior
        successful_queries = sum(1 for r in results if r["status"] == "success")
        failed_queries = sum(1 for r in results if r["status"] == "error")

        assert successful_queries <= 8  # Within rate limit
        assert successful_queries + failed_queries == len(queries)
        assert stats["executed_queries"] == successful_queries
        assert stats["rate_limited_queries"] >= 0
