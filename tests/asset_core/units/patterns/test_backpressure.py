# ABOUTME: Unit tests for the backpressure controller abstract interface and concrete implementations
# ABOUTME: Validates the backpressure pattern implementation and contract compliance with functional scenarios

import asyncio
from abc import ABC
from collections import deque
from typing import Any

import pytest

from asset_core.patterns.backpressure import AbstractBackpressureController


class ConcreteBackpressureController(AbstractBackpressureController):
    """Concrete implementation for testing the abstract interface."""

    def __init__(self, should_throttle_result: bool = False):
        self._should_throttle_result = should_throttle_result

    async def should_throttle(self) -> bool:
        """Test implementation of should_throttle method."""
        return self._should_throttle_result


class QueueBasedBackpressureController(AbstractBackpressureController):
    """Queue-based backpressure controller for comprehensive functional testing.

    This implementation uses high and low watermarks to control backpressure:
    - Triggers backpressure when queue size reaches high watermark
    - Releases backpressure when queue size drops to low watermark
    - Provides hysteresis to prevent oscillation around threshold
    """

    def __init__(self, high_watermark: int = 10, low_watermark: int = 5, initial_size: int = 0) -> None:
        """Initialize queue-based backpressure controller.

        Args:
            high_watermark: Queue size threshold to trigger backpressure
            low_watermark: Queue size threshold to release backpressure
            initial_size: Initial queue size for testing

        Raises:
            ValueError: If watermarks are invalid
        """
        if high_watermark <= 0 or low_watermark < 0:
            raise ValueError("Watermarks must be non-negative")
        if low_watermark >= high_watermark:
            raise ValueError("Low watermark must be less than high watermark")

        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
        self._queue: deque[Any] = deque()
        self._is_throttling = False
        self._throttle_count = 0
        self._release_count = 0

        # Initialize queue with specified size
        for i in range(initial_size):
            self._queue.append(f"initial_item_{i}")

    async def should_throttle(self) -> bool:
        """Determine if throttling should be applied based on queue state.

        Uses hysteresis pattern:
        - If not currently throttling: trigger when size >= high_watermark
        - If currently throttling: release when size <= low_watermark

        Returns:
            True if throttling should be applied, False otherwise
        """
        await asyncio.sleep(0.001)  # Simulate async operation

        current_size = len(self._queue)

        if not self._is_throttling and current_size >= self.high_watermark:
            self._is_throttling = True
            self._throttle_count += 1
        elif self._is_throttling and current_size <= self.low_watermark:
            self._is_throttling = False
            self._release_count += 1

        return self._is_throttling

    def add_item(self, item: Any) -> bool:
        """Add item to queue if not currently throttling.

        Args:
            item: Item to add to queue

        Returns:
            True if item was added, False if rejected due to throttling
        """
        if len(self._queue) >= self.high_watermark:
            return False

        self._queue.append(item)
        return True

    def remove_item(self) -> Any | None:
        """Remove and return item from queue.

        Returns:
            Item from queue or None if queue is empty
        """
        try:
            return self._queue.popleft()
        except IndexError:
            return None

    def clear_queue(self) -> None:
        """Clear all items from queue."""
        self._queue.clear()

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def is_throttling(self) -> bool:
        """Check if currently in throttling state."""
        return self._is_throttling

    def get_stats(self) -> dict[str, Any]:
        """Get controller statistics."""
        return {
            "queue_size": len(self._queue),
            "high_watermark": self.high_watermark,
            "low_watermark": self.low_watermark,
            "is_throttling": self._is_throttling,
            "throttle_count": self._throttle_count,
            "release_count": self._release_count,
        }


class TestAbstractBackpressureController:
    """Test the AbstractBackpressureController interface."""

    def test_is_abstract_base_class(self) -> None:
        """Test that AbstractBackpressureController is an abstract class."""
        assert issubclass(AbstractBackpressureController, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            AbstractBackpressureController()  # type: ignore[abstract]

    def test_has_required_abstract_method(self) -> None:
        """Test that should_throttle method is marked as abstract."""
        abstract_methods = AbstractBackpressureController.__abstractmethods__
        assert "should_throttle" in abstract_methods

    def test_concrete_implementation_no_throttle(self) -> None:
        """Test concrete implementation returning False (no throttling)."""
        controller = ConcreteBackpressureController(should_throttle_result=False)

        # Test the interface contract
        assert hasattr(controller, "should_throttle")
        assert callable(controller.should_throttle)

    def test_concrete_implementation_with_throttle(self) -> None:
        """Test concrete implementation returning True (throttling enabled)."""
        controller = ConcreteBackpressureController(should_throttle_result=True)

        # Test the interface contract
        assert hasattr(controller, "should_throttle")
        assert callable(controller.should_throttle)

    @pytest.mark.asyncio
    async def test_should_throttle_returns_false(self) -> None:
        """Test should_throttle method returning False."""
        controller = ConcreteBackpressureController(should_throttle_result=False)
        result = await controller.should_throttle()
        assert result is False

    @pytest.mark.asyncio
    async def test_should_throttle_returns_true(self) -> None:
        """Test should_throttle method returning True."""
        controller = ConcreteBackpressureController(should_throttle_result=True)
        result = await controller.should_throttle()
        assert result is True

    @pytest.mark.asyncio
    async def test_should_throttle_is_async(self) -> None:
        """Test that should_throttle is an async method."""
        controller = ConcreteBackpressureController()

        # should_throttle should return a coroutine
        coro = controller.should_throttle()
        assert hasattr(coro, "__await__")

        # Clean up the coroutine
        result = await coro
        assert isinstance(result, bool)

    def test_interface_contract_compliance(self) -> None:
        """Test that concrete implementation satisfies the interface contract."""
        controller = ConcreteBackpressureController()

        # Should be an instance of the abstract class
        assert isinstance(controller, AbstractBackpressureController)

        # Should have the required method
        assert hasattr(controller, "should_throttle")

        # Method should be callable
        assert callable(controller.should_throttle)

    def test_multiple_implementations_possible(self) -> None:
        """Test that multiple concrete implementations can coexist."""

        class AlwaysThrottleController(AbstractBackpressureController):
            async def should_throttle(self) -> bool:
                return True

        class NeverThrottleController(AbstractBackpressureController):
            async def should_throttle(self) -> bool:
                return False

        always_controller = AlwaysThrottleController()
        never_controller = NeverThrottleController()

        # Both should be instances of the abstract class
        assert isinstance(always_controller, AbstractBackpressureController)
        assert isinstance(never_controller, AbstractBackpressureController)

    @pytest.mark.asyncio
    async def test_polymorphic_behavior(self) -> None:
        """Test polymorphic behavior of different implementations."""

        class ThrottleController(AbstractBackpressureController):
            async def should_throttle(self) -> bool:
                return True

        class NoThrottleController(AbstractBackpressureController):
            async def should_throttle(self) -> bool:
                return False

        controllers = [
            ThrottleController(),
            NoThrottleController(),
            ConcreteBackpressureController(True),
            ConcreteBackpressureController(False),
        ]

        expected_results = [True, False, True, False]

        for controller, expected in zip(controllers, expected_results, strict=False):
            result = await controller.should_throttle()
            assert result == expected

    def test_docstring_presence(self) -> None:
        """Test that the abstract class has proper documentation."""
        assert AbstractBackpressureController.__doc__ is not None
        assert len(AbstractBackpressureController.__doc__.strip()) > 0

        # Check method docstring
        method = AbstractBackpressureController.should_throttle
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_method_signature(self) -> None:
        """Test that should_throttle method has the correct signature."""
        import inspect

        # Get the signature of the abstract method
        sig = inspect.signature(AbstractBackpressureController.should_throttle)

        # Should only have 'self' parameter
        params = list(sig.parameters.keys())
        assert params == ["self"]

        # Should have bool return annotation
        assert sig.return_annotation is bool


class TestQueueBasedBackpressureController:
    """Test suite for queue-based backpressure controller functional scenarios."""

    @pytest.fixture
    def controller(self) -> QueueBasedBackpressureController:
        """Provide a standard queue-based backpressure controller for testing."""
        return QueueBasedBackpressureController(high_watermark=5, low_watermark=2, initial_size=0)

    def test_initialization_valid_parameters(self) -> None:
        """Test controller initialization with valid parameters.

        Verifies:
        - Controller initializes with correct watermarks
        - Initial queue state is correct
        - Statistics are properly initialized
        """
        controller = QueueBasedBackpressureController(high_watermark=10, low_watermark=3, initial_size=5)

        assert controller.high_watermark == 10
        assert controller.low_watermark == 3
        assert controller.get_queue_size() == 5
        assert not controller.is_throttling()

        stats = controller.get_stats()
        assert stats["queue_size"] == 5
        assert stats["throttle_count"] == 0
        assert stats["release_count"] == 0

    def test_initialization_invalid_parameters(self) -> None:
        """Test controller initialization with invalid parameters.

        Verifies:
        - Raises ValueError for invalid watermark combinations
        - Prevents creation of invalid controller states
        """
        # Test negative watermarks
        with pytest.raises(ValueError, match="Watermarks must be non-negative"):
            QueueBasedBackpressureController(high_watermark=-1, low_watermark=2)

        with pytest.raises(ValueError, match="Watermarks must be non-negative"):
            QueueBasedBackpressureController(high_watermark=5, low_watermark=-1)

        # Test invalid watermark relationship
        with pytest.raises(ValueError, match="Low watermark must be less than high watermark"):
            QueueBasedBackpressureController(high_watermark=5, low_watermark=5)

        with pytest.raises(ValueError, match="Low watermark must be less than high watermark"):
            QueueBasedBackpressureController(high_watermark=3, low_watermark=7)

    @pytest.mark.asyncio
    async def test_normal_flow_no_backpressure(self, controller: QueueBasedBackpressureController) -> None:
        """Test normal flow scenario where queue stays below high watermark.

        Test Description:
        Verifies that items pass through normally when queue size is below
        the high watermark threshold, ensuring no backpressure is applied.

        Test Steps:
        1. Add items below high watermark
        2. Verify no throttling occurs
        3. Check controller state remains normal

        Expected Results:
        - should_throttle() returns False
        - Items are successfully added to queue
        - Controller remains in non-throttling state
        """
        # Add items below high watermark (high_watermark = 5)
        for i in range(4):
            success = controller.add_item(f"item_{i}")
            assert success is True

        assert controller.get_queue_size() == 4

        # Should not throttle with normal load
        result = await controller.should_throttle()
        assert result is False
        assert not controller.is_throttling()

        # Verify stats
        stats = controller.get_stats()
        assert stats["throttle_count"] == 0
        assert stats["is_throttling"] is False

    @pytest.mark.asyncio
    async def test_backpressure_trigger_at_high_watermark(self, controller: QueueBasedBackpressureController) -> None:
        """Test backpressure activation when queue reaches high watermark.

        Test Description:
        Verifies that backpressure is triggered when the queue size reaches
        the high watermark threshold, activating flow control.

        Test Steps:
        1. Fill queue to high watermark
        2. Check that throttling is triggered
        3. Verify controller enters throttling state

        Expected Results:
        - should_throttle() returns True when at high watermark
        - Controller transitions to throttling state
        - Throttle count increments
        """
        # Fill queue to high watermark (5 items)
        for i in range(5):
            controller.add_item(f"item_{i}")

        assert controller.get_queue_size() == 5

        # Should trigger backpressure at high watermark
        result = await controller.should_throttle()
        assert result is True
        assert controller.is_throttling()

        # Verify throttle was triggered
        stats = controller.get_stats()
        assert stats["throttle_count"] == 1
        assert stats["is_throttling"] is True

    @pytest.mark.asyncio
    async def test_backpressure_release_at_low_watermark(self, controller: QueueBasedBackpressureController) -> None:
        """Test backpressure release when queue drops to low watermark.

        Test Description:
        Verifies that backpressure is released when the queue size drops
        to the low watermark threshold, restoring normal flow.

        Test Steps:
        1. Trigger backpressure by filling queue
        2. Drain queue to low watermark
        3. Verify throttling is released

        Expected Results:
        - should_throttle() returns False when at low watermark
        - Controller transitions from throttling to normal state
        - Release count increments
        """
        # First trigger backpressure
        for i in range(5):
            controller.add_item(f"item_{i}")

        await controller.should_throttle()  # Trigger throttling
        assert controller.is_throttling()

        # Drain queue to low watermark (2 items)
        for _ in range(3):
            controller.remove_item()

        assert controller.get_queue_size() == 2

        # Should release backpressure at low watermark
        result = await controller.should_throttle()
        assert result is False
        assert not controller.is_throttling()

        # Verify release was triggered
        stats = controller.get_stats()
        assert stats["release_count"] == 1
        assert stats["is_throttling"] is False

    @pytest.mark.asyncio
    async def test_producer_blocking_during_backpressure(self, controller: QueueBasedBackpressureController) -> None:
        """Test that producers are effectively blocked during backpressure.

        Test Description:
        Verifies that when backpressure is active, producers cannot add
        new items to the queue, implementing proper flow control.

        Test Steps:
        1. Fill queue to trigger backpressure
        2. Attempt to add more items
        3. Verify items are rejected

        Expected Results:
        - Items are rejected when backpressure is active
        - Queue size remains at high watermark
        - Controller maintains throttling state
        """
        # Fill queue to high watermark to trigger backpressure
        for i in range(5):
            controller.add_item(f"item_{i}")

        await controller.should_throttle()  # Trigger throttling
        assert controller.is_throttling()

        # Attempt to add more items - should be blocked
        success1 = controller.add_item("blocked_item_1")
        success2 = controller.add_item("blocked_item_2")

        assert success1 is False
        assert success2 is False
        assert controller.get_queue_size() == 5  # Size unchanged

        # Should still be throttling
        result = await controller.should_throttle()
        assert result is True
        assert controller.is_throttling()

    @pytest.mark.asyncio
    async def test_hysteresis_prevents_oscillation(self, controller: QueueBasedBackpressureController) -> None:
        """Test hysteresis pattern prevents rapid oscillation around threshold.

        Test Description:
        Verifies that the controller uses different thresholds for activating
        and deactivating backpressure, preventing rapid state changes.

        Test Steps:
        1. Trigger backpressure at high watermark
        2. Reduce queue size slightly (but above low watermark)
        3. Verify throttling continues
        4. Reduce to low watermark
        5. Verify throttling stops

        Expected Results:
        - Throttling persists between low and high watermarks
        - Only releases when reaching low watermark exactly
        - Prevents oscillation between states
        """
        # Trigger backpressure (high_watermark = 5)
        for i in range(5):
            controller.add_item(f"item_{i}")

        await controller.should_throttle()  # Trigger
        assert controller.is_throttling()

        # Remove one item (size = 4, still above low_watermark = 2)
        controller.remove_item()
        assert controller.get_queue_size() == 4

        # Should still be throttling (hysteresis)
        result = await controller.should_throttle()
        assert result is True
        assert controller.is_throttling()

        # Remove more items to reach low watermark
        controller.remove_item()  # size = 3
        controller.remove_item()  # size = 2
        assert controller.get_queue_size() == 2

        # Should now release throttling
        result = await controller.should_throttle()
        assert result is False
        assert not controller.is_throttling()

    @pytest.mark.asyncio
    async def test_boundary_condition_empty_queue(self, controller: QueueBasedBackpressureController) -> None:
        """Test boundary condition with empty queue.

        Test Description:
        Verifies correct behavior when queue is completely empty,
        ensuring no unexpected throttling occurs.

        Test Steps:
        1. Ensure queue starts empty
        2. Check throttling state
        3. Attempt queue operations

        Expected Results:
        - No throttling with empty queue
        - Queue operations handle empty state gracefully
        - Controller statistics are correct
        """
        assert controller.get_queue_size() == 0

        # Should not throttle with empty queue
        result = await controller.should_throttle()
        assert result is False
        assert not controller.is_throttling()

        # Removing from empty queue should return None
        item = controller.remove_item()
        assert item is None

        # Adding to empty queue should succeed
        success = controller.add_item("first_item")
        assert success is True
        assert controller.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_boundary_condition_full_queue(self, controller: QueueBasedBackpressureController) -> None:
        """Test boundary condition with queue at maximum capacity.

        Test Description:
        Verifies correct behavior when queue is at high watermark,
        ensuring proper throttling activation.

        Test Steps:
        1. Fill queue to high watermark
        2. Verify throttling activates
        3. Test operations at capacity

        Expected Results:
        - Throttling activates at high watermark
        - Additional items are rejected
        - Controller handles full queue state properly
        """
        # Fill to high watermark (5 items)
        for i in range(5):
            controller.add_item(f"item_{i}")

        assert controller.get_queue_size() == 5

        # Should throttle at full capacity
        result = await controller.should_throttle()
        assert result is True
        assert controller.is_throttling()

        # Adding more items should fail
        success = controller.add_item("overflow_item")
        assert success is False
        assert controller.get_queue_size() == 5  # Unchanged

    @pytest.mark.asyncio
    async def test_boundary_condition_exact_watermarks(self, controller: QueueBasedBackpressureController) -> None:
        """Test behavior at exact watermark boundaries.

        Test Description:
        Verifies precise behavior when queue size equals watermark values,
        ensuring correct threshold detection.

        Test Steps:
        1. Test at low watermark exactly
        2. Test at high watermark exactly
        3. Test transitions at exact boundaries

        Expected Results:
        - Correct throttling state at exact watermark values
        - Proper state transitions at boundaries
        - Accurate threshold detection
        """
        # Test at low watermark exactly (2 items)
        for i in range(2):
            controller.add_item(f"item_{i}")

        assert controller.get_queue_size() == 2
        result = await controller.should_throttle()
        assert result is False  # Should not throttle at low watermark

        # Add items to reach high watermark exactly (5 items)
        for i in range(2, 5):
            controller.add_item(f"item_{i}")

        assert controller.get_queue_size() == 5
        result = await controller.should_throttle()
        assert result is True  # Should throttle at high watermark

        # Test release at low watermark exactly
        while controller.get_queue_size() > 2:
            controller.remove_item()

        assert controller.get_queue_size() == 2
        result = await controller.should_throttle()
        assert result is False  # Should release at low watermark

    @pytest.mark.asyncio
    async def test_multiple_throttle_release_cycles(self, controller: QueueBasedBackpressureController) -> None:
        """Test multiple cycles of throttling and release.

        Test Description:
        Verifies that controller handles multiple cycles of backpressure
        activation and deactivation correctly.

        Test Steps:
        1. Perform multiple fill/drain cycles
        2. Verify each cycle triggers/releases correctly
        3. Check statistics track all cycles

        Expected Results:
        - Each cycle properly triggers and releases
        - Statistics accurately count all transitions
        - Controller state remains consistent
        """
        # Perform 3 complete cycles
        for cycle in range(3):
            # Fill to trigger backpressure
            for i in range(5):
                controller.add_item(f"cycle_{cycle}_item_{i}")

            result = await controller.should_throttle()
            assert result is True

            # Drain to release backpressure
            while controller.get_queue_size() > 2:
                controller.remove_item()

            result = await controller.should_throttle()
            assert result is False

        # Verify statistics
        stats = controller.get_stats()
        assert stats["throttle_count"] == 3
        assert stats["release_count"] == 3
        assert not stats["is_throttling"]

    @pytest.mark.asyncio
    async def test_concurrent_should_throttle_calls(self, controller: QueueBasedBackpressureController) -> None:
        """Test concurrent calls to should_throttle method.

        Test Description:
        Verifies that multiple concurrent calls to should_throttle
        behave correctly and maintain consistent state.

        Test Steps:
        1. Set up queue state
        2. Make multiple concurrent should_throttle calls
        3. Verify all calls return consistent results

        Expected Results:
        - All concurrent calls return same result
        - Controller state remains consistent
        - No race conditions occur
        """
        # Fill queue to trigger backpressure
        for i in range(5):
            controller.add_item(f"item_{i}")

        # Make multiple concurrent calls
        tasks = [controller.should_throttle() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All results should be True (throttling)
        assert all(result is True for result in results)
        assert controller.is_throttling()

        # Drain queue and test concurrent calls for release
        controller.clear_queue()
        for i in range(2):  # At low watermark
            controller.add_item(f"new_item_{i}")

        tasks = [controller.should_throttle() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Should eventually all return False (not throttling)
        assert not controller.is_throttling()

    def test_queue_operations_integration(self, controller: QueueBasedBackpressureController) -> None:
        """Test integration between queue operations and backpressure state.

        Test Description:
        Verifies that queue operations (add/remove) work correctly
        in conjunction with backpressure state management.

        Test Steps:
        1. Test adding items with different queue states
        2. Test removing items with different queue states
        3. Verify operations affect backpressure correctly

        Expected Results:
        - Queue operations respect backpressure state
        - Operations correctly modify queue size
        - Integration between operations and throttling works
        """
        # Test adding items when not throttling
        for i in range(3):
            success = controller.add_item(f"item_{i}")
            assert success is True

        assert controller.get_queue_size() == 3

        # Fill to capacity
        for i in range(3, 5):
            success = controller.add_item(f"item_{i}")
            assert success is True

        # Should not accept more items at capacity
        success = controller.add_item("overflow")
        assert success is False

        # Test removing items
        item = controller.remove_item()
        assert item == "item_0"
        assert controller.get_queue_size() == 4

        # Clear and verify
        controller.clear_queue()
        assert controller.get_queue_size() == 0
        assert controller.remove_item() is None

    def test_controller_statistics_accuracy(self, controller: QueueBasedBackpressureController) -> None:
        """Test accuracy of controller statistics reporting.

        Test Description:
        Verifies that controller statistics accurately reflect
        the current state and historical operations.

        Test Steps:
        1. Perform various operations
        2. Check statistics at each step
        3. Verify accuracy of all reported metrics

        Expected Results:
        - Statistics accurately reflect current state
        - Historical counts are correct
        - All metrics are properly maintained
        """
        initial_stats = controller.get_stats()
        assert initial_stats["queue_size"] == 0
        assert initial_stats["throttle_count"] == 0
        assert initial_stats["release_count"] == 0
        assert not initial_stats["is_throttling"]

        # Add items and check stats
        controller.add_item("test_item")
        stats = controller.get_stats()
        assert stats["queue_size"] == 1
        assert stats["high_watermark"] == 5
        assert stats["low_watermark"] == 2

        # Statistics should be consistent with controller state
        assert stats["is_throttling"] == controller.is_throttling()
        assert stats["queue_size"] == controller.get_queue_size()

    @pytest.mark.asyncio
    async def test_edge_case_rapid_state_changes(self, controller: QueueBasedBackpressureController) -> None:
        """Test edge case with rapid state changes.

        Test Description:
        Verifies controller handles rapid changes in queue state
        without inconsistencies or unexpected behavior.

        Test Steps:
        1. Rapidly alternate between adding and removing items
        2. Check throttling state at each step
        3. Verify state transitions are consistent

        Expected Results:
        - Controller handles rapid changes correctly
        - State transitions remain consistent
        - No unexpected behavior occurs
        """
        # Rapidly alternate operations around high watermark
        for _ in range(10):
            # Fill to high watermark
            while controller.get_queue_size() < 5:
                controller.add_item("temp_item")

            throttle_result = await controller.should_throttle()
            assert throttle_result is True

            # Drain to low watermark
            while controller.get_queue_size() > 2:
                controller.remove_item()

            throttle_result = await controller.should_throttle()
            assert throttle_result is False

        # Verify final state is consistent
        stats = controller.get_stats()
        assert stats["throttle_count"] == 10
        assert stats["release_count"] == 10
        assert not controller.is_throttling()
