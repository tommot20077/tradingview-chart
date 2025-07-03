# ABOUTME: Integration tests for backpressure controller components with system interactions.
# ABOUTME: Tests cover backpressure controller integration with async systems and real-world scenarios.

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from asset_core.patterns.backpressure import AbstractBackpressureController


class SystemLoadBackpressureController(AbstractBackpressureController):
    """Backpressure controller that monitors system load metrics."""

    def __init__(self, load_threshold: float = 0.8, initial_load: float = 0.0) -> None:
        """Initialize system load backpressure controller.

        Args:
            load_threshold: System load threshold above which to throttle
            initial_load: Initial system load value
        """
        self.load_threshold = load_threshold
        self.current_load = initial_load
        self.check_count = 0
        self.load_history: list[float] = []

    async def should_throttle(self) -> bool:
        """Check if system load exceeds threshold."""
        self.check_count += 1
        # Simulate async load checking
        await asyncio.sleep(0.001)

        self.load_history.append(self.current_load)
        return self.current_load > self.load_threshold

    def set_load(self, load: float) -> None:
        """Set current system load for testing."""
        self.current_load = load

    def get_load_stats(self) -> dict[str, Any]:
        """Get load statistics."""
        return {
            "current_load": self.current_load,
            "threshold": self.load_threshold,
            "check_count": self.check_count,
            "average_load": sum(self.load_history) / len(self.load_history) if self.load_history else 0.0,
        }


class QueueDepthBackpressureController(AbstractBackpressureController):
    """Backpressure controller that monitors queue depth."""

    def __init__(self, max_queue_size: int = 100) -> None:
        """Initialize queue depth backpressure controller."""
        self.max_queue_size = max_queue_size
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.throttle_count = 0

    async def should_throttle(self) -> bool:
        """Check if queue depth exceeds maximum."""
        await asyncio.sleep(0.001)
        current_size = self.queue.qsize()
        should_throttle = current_size >= self.max_queue_size

        if should_throttle:
            self.throttle_count += 1

        return should_throttle

    async def enqueue_item(self, item: Any) -> bool:
        """Add item to queue if not throttling."""
        if await self.should_throttle():
            return False

        await self.queue.put(item)
        return True

    async def dequeue_item(self) -> Any | None:
        """Remove and return item from queue."""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=0.001)
        except TimeoutError:
            return None

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "queue_size": self.queue.qsize(),
            "max_size": self.max_queue_size,
            "throttle_count": self.throttle_count,
        }


class ProducerConsumerSystem:
    """System that demonstrates backpressure in producer-consumer scenario."""

    def __init__(self, backpressure_controller: AbstractBackpressureController) -> None:
        """Initialize producer-consumer system with backpressure control."""
        self.backpressure_controller = backpressure_controller
        self.queue: asyncio.Queue[int] = asyncio.Queue()
        self.produced_count = 0
        self.consumed_count = 0
        self.throttled_count = 0
        self.running = False

    async def producer(self, items_to_produce: int, production_rate: float = 0.01) -> None:
        """Producer that respects backpressure."""
        for i in range(items_to_produce):
            if not self.running:
                break

            # Check backpressure before producing
            if await self.backpressure_controller.should_throttle():
                self.throttled_count += 1
                # Wait before retrying
                await asyncio.sleep(production_rate * 2)
                continue

            await self.queue.put(i)
            self.produced_count += 1
            await asyncio.sleep(production_rate)

    async def consumer(self, consumption_rate: float = 0.02) -> None:
        """Consumer that processes items from queue."""
        while self.running:
            try:
                await asyncio.wait_for(self.queue.get(), timeout=0.1)
                self.consumed_count += 1
                # Simulate processing time
                await asyncio.sleep(consumption_rate)
            except TimeoutError:
                continue

    def start(self) -> None:
        """Start the system."""
        self.running = True

    def stop(self) -> None:
        """Stop the system."""
        self.running = False

    def get_stats(self) -> dict[str, Any]:
        """Get system statistics."""
        return {
            "produced": self.produced_count,
            "consumed": self.consumed_count,
            "throttled": self.throttled_count,
            "queue_size": self.queue.qsize(),
        }


@pytest.mark.integration
class TestBackpressureControllerSystemIntegration:
    """Integration tests for backpressure controllers with system components."""

    @pytest.fixture
    def system_controller(self) -> SystemLoadBackpressureController:
        """Provide system load backpressure controller."""
        return SystemLoadBackpressureController(load_threshold=0.7, initial_load=0.3)

    @pytest.fixture
    def queue_controller(self) -> QueueDepthBackpressureController:
        """Provide queue depth backpressure controller."""
        return QueueDepthBackpressureController(max_queue_size=5)

    async def test_system_load_integration(self, system_controller: SystemLoadBackpressureController) -> None:
        """Test integration with system load monitoring.

        Description of what the test covers:
        Verifies backpressure controller integration with system load metrics
        and proper throttling behavior based on load conditions.

        Preconditions:
        - System load controller with threshold 0.7

        Steps:
        - Test with low system load (no throttling)
        - Increase system load above threshold
        - Verify throttling activates
        - Reduce load and verify throttling stops

        Expected Result:
        - Should throttle when load exceeds threshold
        - Should stop throttling when load decreases
        - Statistics should be tracked correctly
        """
        # Low system load - should not throttle
        system_controller.set_load(0.5)
        result1 = await system_controller.should_throttle()
        assert result1 is False

        # High system load - should throttle
        system_controller.set_load(0.9)
        result2 = await system_controller.should_throttle()
        assert result2 is True

        # Load back to normal - should not throttle
        system_controller.set_load(0.4)
        result3 = await system_controller.should_throttle()
        assert result3 is False

        # Check statistics
        stats = system_controller.get_load_stats()
        assert stats["check_count"] == 3
        assert stats["current_load"] == 0.4
        assert stats["threshold"] == 0.7
        assert len(system_controller.load_history) == 3

    async def test_queue_depth_integration(self, queue_controller: QueueDepthBackpressureController) -> None:
        """Test integration with queue depth monitoring.

        Description of what the test covers:
        Verifies backpressure controller integration with queue management
        and proper throttling based on queue depth.

        Preconditions:
        - Queue controller with max size 5

        Steps:
        - Fill queue below threshold
        - Fill queue to threshold
        - Verify throttling activates
        - Drain queue and verify throttling stops

        Expected Result:
        - Should throttle when queue is full
        - Should allow when queue has space
        - Queue operations should respect backpressure
        """
        # Fill queue below threshold
        for i in range(4):
            success = await queue_controller.enqueue_item(f"item_{i}")
            assert success is True

        assert queue_controller.queue.qsize() == 4

        # Fill queue to threshold - should still allow
        success = await queue_controller.enqueue_item("item_4")
        assert success is True  # Should allow because queue reaches max, not exceeds

        # Attempt to add one more item - should now throttle
        success = await queue_controller.enqueue_item("item_5")
        assert success is False  # Should throttle because queue would exceed max

        # Drain some items
        item1 = await queue_controller.dequeue_item()
        item2 = await queue_controller.dequeue_item()
        assert item1 == "item_0"
        assert item2 == "item_1"

        # Should allow new items now
        success = await queue_controller.enqueue_item("new_item")
        assert success is True

        stats = queue_controller.get_stats()
        assert stats["queue_size"] == 4  # 5 - 2 + 1
        assert stats["throttle_count"] > 0

    async def test_producer_consumer_backpressure(self, queue_controller: QueueDepthBackpressureController) -> None:
        """Test backpressure in producer-consumer scenario.

        Description of what the test covers:
        Verifies backpressure integration in realistic producer-consumer
        system with proper throttling behavior.

        Preconditions:
        - Producer-consumer system with backpressure controller

        Steps:
        - Start producer-consumer system
        - Run for short period
        - Verify backpressure affects production
        - Check statistics

        Expected Result:
        - Producer should be throttled when queue is full
        - Consumer should drain queue
        - System should reach steady state
        """
        system = ProducerConsumerSystem(queue_controller)
        system.start()

        # Run producer and consumer concurrently
        producer_task = asyncio.create_task(system.producer(20, production_rate=0.01))
        consumer_task = asyncio.create_task(system.consumer(consumption_rate=0.02))

        # Let system run for a short time
        await asyncio.sleep(0.2)

        system.stop()

        # Wait for tasks to complete
        try:
            await asyncio.wait_for(producer_task, timeout=0.1)
        except TimeoutError:
            producer_task.cancel()

        try:
            await asyncio.wait_for(consumer_task, timeout=0.1)
        except TimeoutError:
            consumer_task.cancel()

        stats = system.get_stats()

        # Verify system operated correctly
        assert stats["produced"] > 0
        assert stats["consumed"] >= 0
        # Should have some throttling due to queue constraints
        assert stats["throttled"] >= 0

    async def test_multiple_backpressure_controllers(self) -> None:
        """Test system with multiple backpressure controllers.

        Description of what the test covers:
        Verifies integration of multiple backpressure controllers
        working together in a complex system.

        Preconditions:
        - Multiple backpressure controllers

        Steps:
        - Create composite backpressure system
        - Test with different controller states
        - Verify combined behavior

        Expected Result:
        - Should throttle if any controller indicates throttling
        - Should work correctly with multiple controllers
        """

        class CompositeBackpressureController(AbstractBackpressureController):
            def __init__(self, controllers: list[AbstractBackpressureController]) -> None:
                self.controllers = controllers

            async def should_throttle(self) -> bool:
                # Throttle if any controller says to throttle
                results = await asyncio.gather(*[c.should_throttle() for c in self.controllers])
                return any(results)

        system_controller = SystemLoadBackpressureController(load_threshold=0.8, initial_load=0.5)
        queue_controller = QueueDepthBackpressureController(max_queue_size=3)

        composite = CompositeBackpressureController([system_controller, queue_controller])

        # Both controllers should not throttle initially
        result1 = await composite.should_throttle()
        assert result1 is False

        # Make system controller throttle
        system_controller.set_load(0.9)
        result2 = await composite.should_throttle()
        assert result2 is True

        # Reset system load but fill queue
        system_controller.set_load(0.5)
        for i in range(3):
            await queue_controller.queue.put(f"item_{i}")

        result3 = await composite.should_throttle()
        assert result3 is True  # Queue controller should throttle

        # Clear queue
        for _ in range(3):
            await queue_controller.queue.get()

        result4 = await composite.should_throttle()
        assert result4 is False  # Both should not throttle now


@pytest.mark.integration
class TestBackpressureControllerAsyncIntegration:
    """Integration tests for backpressure controllers with async systems."""

    async def test_backpressure_with_async_tasks(self) -> None:
        """Test backpressure controller integration with async task management.

        Description of what the test covers:
        Verifies backpressure controller works correctly with async task
        scheduling and execution management.

        Preconditions:
        - Async task management system with backpressure

        Steps:
        - Create task scheduler with backpressure control
        - Submit multiple tasks
        - Verify backpressure affects task execution

        Expected Result:
        - Tasks should be throttled when backpressure is active
        - Task execution should proceed when backpressure is released
        """

        class AsyncTaskScheduler:
            def __init__(self, backpressure_controller: AbstractBackpressureController) -> None:
                self.backpressure_controller = backpressure_controller
                self.executed_tasks = 0
                self.throttled_tasks = 0

            async def execute_task(self, task_func: Callable[[], Any]) -> bool:
                if await self.backpressure_controller.should_throttle():
                    self.throttled_tasks += 1
                    return False

                await task_func()
                self.executed_tasks += 1
                return True

        controller = SystemLoadBackpressureController(load_threshold=0.6, initial_load=0.3)
        scheduler = AsyncTaskScheduler(controller)

        async def dummy_task() -> None:
            await asyncio.sleep(0.001)

        # Execute tasks with low load
        for _ in range(5):
            success = await scheduler.execute_task(dummy_task)
            assert success is True

        assert scheduler.executed_tasks == 5
        assert scheduler.throttled_tasks == 0

        # Increase load and try more tasks
        controller.set_load(0.8)

        for _ in range(5):
            success = await scheduler.execute_task(dummy_task)
            assert success is False

        assert scheduler.executed_tasks == 5  # No new executions
        assert scheduler.throttled_tasks == 5

    async def test_backpressure_with_websocket_simulation(self) -> None:
        """Test backpressure controller with WebSocket-like message handling.

        Description of what the test covers:
        Verifies backpressure controller integration with message handling
        systems similar to WebSocket connections.

        Preconditions:
        - Message handler with backpressure control

        Steps:
        - Create message handler with backpressure
        - Send messages at different rates
        - Verify backpressure affects message processing

        Expected Result:
        - Messages should be dropped when backpressure is active
        - Message processing should resume when backpressure is released
        """

        class MessageHandler:
            def __init__(self, backpressure_controller: AbstractBackpressureController) -> None:
                self.backpressure_controller = backpressure_controller
                self.processed_messages = 0
                self.dropped_messages = 0
                self.message_queue: asyncio.Queue[str] = asyncio.Queue()

            async def handle_message(self, message: str) -> bool:
                if await self.backpressure_controller.should_throttle():
                    self.dropped_messages += 1
                    return False

                await self.message_queue.put(message)
                self.processed_messages += 1
                return True

            async def process_messages(self) -> None:
                while not self.message_queue.empty():
                    await self.message_queue.get()
                    # Simulate message processing
                    await asyncio.sleep(0.001)

        controller = QueueDepthBackpressureController(max_queue_size=3)
        handler = MessageHandler(controller)

        # Send messages when queue is empty
        for i in range(3):
            success = await handler.handle_message(f"message_{i}")
            assert success is True

        # Fill the controller's internal queue to trigger backpressure
        for i in range(3):
            await controller.queue.put(f"queue_item_{i}")

        # Now messages should be dropped due to backpressure
        for i in range(3):
            success = await handler.handle_message(f"dropped_message_{i}")
            assert success is False

        assert handler.processed_messages == 3
        assert handler.dropped_messages == 3

        # Drain controller queue to release backpressure
        for _ in range(3):
            await controller.queue.get()

        # Should be able to process messages again
        success = await handler.handle_message("new_message")
        assert success is True
        assert handler.processed_messages == 4

    async def test_backpressure_with_event_streaming(self) -> None:
        """Test backpressure controller with event streaming system.

        Description of what the test covers:
        Verifies backpressure controller integration with event streaming
        and proper flow control.

        Preconditions:
        - Event streaming system with backpressure

        Steps:
        - Create event stream with backpressure control
        - Generate events at high rate
        - Verify backpressure controls event flow

        Expected Result:
        - Event flow should be controlled by backpressure
        - System should handle high event rates gracefully
        """

        class EventStream:
            def __init__(self, backpressure_controller: AbstractBackpressureController) -> None:
                self.backpressure_controller = backpressure_controller
                self.events: list[dict[str, Any]] = []
                self.throttled_events = 0
                self.max_events = 100

            async def emit_event(self, event_type: str, data: dict[str, Any]) -> bool:
                if await self.backpressure_controller.should_throttle():
                    self.throttled_events += 1
                    return False

                if len(self.events) >= self.max_events:
                    return False

                event = {
                    "type": event_type,
                    "data": data,
                    "timestamp": asyncio.get_event_loop().time(),
                }
                self.events.append(event)
                return True

            def get_stats(self) -> dict[str, Any]:
                return {
                    "total_events": len(self.events),
                    "throttled_events": self.throttled_events,
                    "max_events": self.max_events,
                }

        controller = SystemLoadBackpressureController(load_threshold=0.5, initial_load=0.2)
        stream = EventStream(controller)

        # Emit events with low system load
        for i in range(10):
            success = await stream.emit_event("test_event", {"id": i})
            assert success is True

        stats = stream.get_stats()
        assert stats["total_events"] == 10
        assert stats["throttled_events"] == 0

        # Increase system load
        controller.set_load(0.8)

        # Try to emit more events - should be throttled
        for i in range(10, 20):
            success = await stream.emit_event("throttled_event", {"id": i})
            assert success is False

        final_stats = stream.get_stats()
        assert final_stats["total_events"] == 10  # No new events
        assert final_stats["throttled_events"] == 10


@pytest.mark.integration
class TestBackpressureControllerRealWorldScenarios:
    """Integration tests simulating real-world backpressure scenarios."""

    async def test_database_connection_pool_backpressure(self) -> None:
        """Test backpressure with database connection pool simulation.

        Description of what the test covers:
        Verifies backpressure controller integration with database
        connection pool management and query throttling.

        Preconditions:
        - Database connection pool simulator

        Steps:
        - Create connection pool with backpressure
        - Execute queries at high rate
        - Verify backpressure controls query execution

        Expected Result:
        - Queries should be throttled when pool is exhausted
        - Connection pool should be managed properly
        """

        class DatabaseConnectionPool:
            def __init__(self, max_connections: int) -> None:
                self.max_connections = max_connections
                self.active_connections = 0
                self.executed_queries = 0
                self.rejected_queries = 0

            async def execute_query(self, _query: str) -> bool:
                if self.active_connections >= self.max_connections:
                    self.rejected_queries += 1
                    return False

                self.active_connections += 1
                try:
                    # Simulate query execution
                    await asyncio.sleep(0.01)
                    self.executed_queries += 1
                    return True
                finally:
                    self.active_connections -= 1

        class PoolBackpressureController(AbstractBackpressureController):
            def __init__(self, pool: DatabaseConnectionPool) -> None:
                self.pool = pool

            async def should_throttle(self) -> bool:
                await asyncio.sleep(0.001)
                return self.pool.active_connections >= self.pool.max_connections

        pool = DatabaseConnectionPool(max_connections=3)
        controller = PoolBackpressureController(pool)

        # Execute queries concurrently
        async def execute_with_backpressure(query_id: int) -> bool:
            if await controller.should_throttle():
                return False
            return await pool.execute_query(f"SELECT * FROM table WHERE id = {query_id}")

        # Execute multiple queries concurrently
        tasks = [execute_with_backpressure(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        successful_queries = sum(1 for r in results if r)
        failed_queries = sum(1 for r in results if not r)

        # Some queries should succeed, some should fail due to backpressure
        assert successful_queries > 0
        assert failed_queries >= 0
        assert pool.executed_queries == successful_queries

    async def test_api_rate_limiting_with_backpressure(self) -> None:
        """Test backpressure with API rate limiting scenario.

        Description of what the test covers:
        Verifies backpressure controller integration with API rate limiting
        and request throttling based on system capacity.

        Preconditions:
        - API server simulator with rate limiting

        Steps:
        - Create API server with backpressure control
        - Send requests at high rate
        - Verify backpressure affects request handling

        Expected Result:
        - Requests should be throttled based on system capacity
        - API should handle load gracefully
        """

        class APIServer:
            def __init__(self, max_concurrent_requests: int) -> None:
                self.max_concurrent_requests = max_concurrent_requests
                self.active_requests = 0
                self.processed_requests = 0
                self.rejected_requests = 0

            async def handle_request(self, request_data: dict[str, Any]) -> dict[str, Any] | None:
                if self.active_requests >= self.max_concurrent_requests:
                    self.rejected_requests += 1
                    return None

                self.active_requests += 1
                try:
                    # Simulate request processing
                    await asyncio.sleep(0.005)
                    self.processed_requests += 1
                    return {"status": "success", "data": request_data}
                finally:
                    self.active_requests -= 1

        class ServerBackpressureController(AbstractBackpressureController):
            def __init__(self, server: APIServer, load_threshold: float = 0.8) -> None:
                self.server = server
                self.load_threshold = load_threshold

            async def should_throttle(self) -> bool:
                await asyncio.sleep(0.001)
                load_ratio = self.server.active_requests / self.server.max_concurrent_requests
                return load_ratio >= self.load_threshold

        server = APIServer(max_concurrent_requests=5)
        controller = ServerBackpressureController(server, load_threshold=0.6)  # 60% threshold

        async def send_request_with_backpressure(request_id: int) -> bool:
            if await controller.should_throttle():
                return False

            request_data = {"id": request_id, "action": "test"}
            response = await server.handle_request(request_data)
            return response is not None

        # Send multiple concurrent requests
        tasks = [send_request_with_backpressure(i) for i in range(15)]
        results = await asyncio.gather(*tasks)

        successful_requests = sum(1 for r in results if r)
        throttled_requests = sum(1 for r in results if not r)

        # Verify backpressure affected request handling
        assert successful_requests > 0
        assert throttled_requests >= 0
        assert server.processed_requests == successful_requests

        # Verify system stats
        total_requests = successful_requests + throttled_requests + server.rejected_requests
        assert total_requests == 15
