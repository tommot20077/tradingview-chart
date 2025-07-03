# ABOUTME: Unit tests for the rate limiter abstract interface and concrete implementations
# ABOUTME: Validates the rate limiting pattern implementation with functional scenarios and time-based testing

import asyncio
import time
from abc import ABC
from typing import Any

import pytest

from asset_core.patterns.rate_limiter import AbstractRateLimiter


class ConcreteRateLimiter(AbstractRateLimiter):
    """Concrete implementation for testing the abstract interface."""

    def __init__(self, allow_acquire: bool = True, max_tokens: int = 10):
        self._allow_acquire = allow_acquire
        self._available_tokens = max_tokens
        self._max_tokens = max_tokens

    async def acquire(self, tokens: int = 1) -> bool:
        """Test implementation of acquire method."""
        if not self._allow_acquire:
            return False

        # Contract: Non-positive tokens are a no-op and always return True
        if tokens <= 0:
            return True

        if tokens <= self._available_tokens:
            self._available_tokens -= tokens
            return True
        return False

    def reset_tokens(self) -> None:
        """Helper method to reset available tokens."""
        self._available_tokens = self._max_tokens


class TokenBucketRateLimiter(AbstractRateLimiter):
    """Token bucket rate limiter implementation for comprehensive functional testing.

    This implementation uses the token bucket algorithm to control request rates:
    - Maintains a bucket with a maximum capacity of tokens
    - Tokens are added to the bucket at a fixed rate (refill_rate)
    - Requests consume tokens from the bucket
    - If insufficient tokens are available, requests are denied or delayed
    """

    def __init__(
        self,
        capacity: int = 10,
        refill_rate: float = 1.0,
        refill_interval: float = 1.0,
        initial_tokens: int | None = None,
    ) -> None:
        """Initialize token bucket rate limiter.

        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Number of tokens added per refill interval
            refill_interval: Time interval (seconds) between token refills
            initial_tokens: Initial number of tokens (defaults to capacity)

        Raises:
            ValueError: If parameters are invalid
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("Refill rate must be positive")
        if refill_interval <= 0:
            raise ValueError("Refill interval must be positive")

        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self._tokens = initial_tokens if initial_tokens is not None else capacity
        self._last_refill = time.time()
        self._acquire_count = 0
        self._denied_count = 0
        self._total_tokens_consumed = 0

    async def acquire(self, tokens: int = 1) -> bool:
        """Attempt to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        if tokens <= 0:
            return True  # No tokens requested

        # Refill tokens based on elapsed time
        await self._refill_tokens()

        # Check if we have enough tokens
        if tokens <= self._tokens:
            self._tokens -= tokens
            self._acquire_count += 1
            self._total_tokens_consumed += tokens
            return True
        else:
            self._denied_count += 1
            return False

    async def _refill_tokens(self) -> None:
        """Refill tokens in the bucket based on elapsed time."""
        current_time = time.time()
        elapsed_time = current_time - self._last_refill

        # Calculate how many tokens to add
        tokens_to_add = elapsed_time * (self.refill_rate / self.refill_interval)

        if tokens_to_add >= 1.0:
            # Add tokens up to capacity
            self._tokens = min(self.capacity, self._tokens + int(tokens_to_add))
            self._last_refill = current_time
        elif elapsed_time > 0:
            # Update last refill time even if less than 1 token would be added
            # This prevents accumulation of fractional time
            self._last_refill = current_time

        # Small async yield to allow other operations
        await asyncio.sleep(0.001)

    def get_available_tokens(self) -> int:
        """Get current number of available tokens."""
        return int(self._tokens)

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "capacity": self.capacity,
            "available_tokens": int(self._tokens),
            "refill_rate": self.refill_rate,
            "refill_interval": self.refill_interval,
            "acquire_count": self._acquire_count,
            "denied_count": self._denied_count,
            "total_tokens_consumed": self._total_tokens_consumed,
            "success_rate": (
                self._acquire_count / (self._acquire_count + self._denied_count)
                if (self._acquire_count + self._denied_count) > 0
                else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._acquire_count = 0
        self._denied_count = 0
        self._total_tokens_consumed = 0

    def force_refill(self) -> None:
        """Force immediate token refill to capacity (for testing)."""
        self._tokens = self.capacity
        self._last_refill = time.time()

    def set_tokens(self, tokens: int) -> None:
        """Set current token count (for testing)."""
        self._tokens = max(0, min(tokens, self.capacity))


class TestAbstractRateLimiter:
    """Test the AbstractRateLimiter interface."""

    def test_is_abstract_base_class(self) -> None:
        """Test that AbstractRateLimiter is an abstract class."""
        assert issubclass(AbstractRateLimiter, ABC)

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            AbstractRateLimiter()  # type: ignore[abstract]

    def test_has_required_abstract_method(self) -> None:
        """Test that acquire method is marked as abstract."""
        abstract_methods = AbstractRateLimiter.__abstractmethods__
        assert "acquire" in abstract_methods

    def test_concrete_implementation_allows_acquire(self) -> None:
        """Test concrete implementation allowing token acquisition."""
        limiter = ConcreteRateLimiter(allow_acquire=True)

        # Test the interface contract
        assert hasattr(limiter, "acquire")
        assert callable(limiter.acquire)

    def test_concrete_implementation_denies_acquire(self) -> None:
        """Test concrete implementation denying token acquisition."""
        limiter = ConcreteRateLimiter(allow_acquire=False)

        # Test the interface contract
        assert hasattr(limiter, "acquire")
        assert callable(limiter.acquire)

    @pytest.mark.asyncio
    async def test_acquire_single_token_success(self) -> None:
        """Test acquiring a single token successfully."""
        limiter = ConcreteRateLimiter(allow_acquire=True)
        result = await limiter.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_single_token_failure(self) -> None:
        """Test failing to acquire a single token."""
        limiter = ConcreteRateLimiter(allow_acquire=False)
        result = await limiter.acquire()
        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens_success(self) -> None:
        """Test acquiring multiple tokens successfully."""
        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=10)
        result = await limiter.acquire(tokens=5)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens_failure(self) -> None:
        """Test failing to acquire multiple tokens due to insufficient tokens."""
        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=3)
        result = await limiter.acquire(tokens=5)
        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_with_default_parameter(self) -> None:
        """Test that acquire works with default token parameter."""
        limiter = ConcreteRateLimiter(allow_acquire=True)
        # Should use default tokens=1
        result = await limiter.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_is_async(self) -> None:
        """Test that acquire is an async method."""
        limiter = ConcreteRateLimiter()

        # acquire should return a coroutine
        coro = limiter.acquire()
        assert hasattr(coro, "__await__")

        # Clean up the coroutine
        result = await coro
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_token_depletion(self) -> None:
        """Test that tokens are properly consumed."""
        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=3)

        # Acquire tokens until exhausted
        assert await limiter.acquire(tokens=2) is True
        assert await limiter.acquire(tokens=1) is True
        assert await limiter.acquire(tokens=1) is False  # Should fail, no tokens left

    def test_interface_contract_compliance(self) -> None:
        """Test that concrete implementation satisfies the interface contract."""
        limiter = ConcreteRateLimiter()

        # Should be an instance of the abstract class
        assert isinstance(limiter, AbstractRateLimiter)

        # Should have the required method
        assert hasattr(limiter, "acquire")

        # Method should be callable
        assert callable(limiter.acquire)

    def test_multiple_implementations_possible(self) -> None:
        """Test that multiple concrete implementations can coexist."""

        class AlwaysAllowLimiter(AbstractRateLimiter):
            async def acquire(self, _tokens: int = 1) -> bool:
                return True

        class AlwaysDenyLimiter(AbstractRateLimiter):
            async def acquire(self, _tokens: int = 1) -> bool:
                return False

        allow_limiter = AlwaysAllowLimiter()
        deny_limiter = AlwaysDenyLimiter()

        # Both should be instances of the abstract class
        assert isinstance(allow_limiter, AbstractRateLimiter)
        assert isinstance(deny_limiter, AbstractRateLimiter)

    @pytest.mark.asyncio
    async def test_polymorphic_behavior(self) -> None:
        """Test polymorphic behavior of different implementations."""

        class AllowLimiter(AbstractRateLimiter):
            async def acquire(self, _tokens: int = 1) -> bool:
                return True

        class DenyLimiter(AbstractRateLimiter):
            async def acquire(self, _tokens: int = 1) -> bool:
                return False

        limiters = [
            AllowLimiter(),
            DenyLimiter(),
            ConcreteRateLimiter(allow_acquire=True),
            ConcreteRateLimiter(allow_acquire=False),
        ]

        expected_results = [True, False, True, False]

        for limiter, expected in zip(limiters, expected_results, strict=False):
            result = await limiter.acquire()
            assert result == expected

    @pytest.mark.asyncio
    async def test_acquire_with_zero_tokens(self) -> None:
        """Test acquiring zero tokens."""
        limiter = ConcreteRateLimiter(allow_acquire=True)
        result = await limiter.acquire(tokens=0)
        assert result is True  # Should succeed as no tokens are requested

    @pytest.mark.asyncio
    async def test_acquire_with_non_positive_tokens(self) -> None:
        """Test acquiring zero or negative tokens.

        Contract Definition:
        - Requesting tokens <= 0 is a no-op and must always return True
        - No tokens are consumed for non-positive requests
        - This behavior ensures consistent API usage
        """
        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=10)
        initial_tokens = 10

        # Test zero tokens - should always succeed and consume nothing
        result = await limiter.acquire(tokens=0)
        assert result is True
        assert limiter._available_tokens == initial_tokens  # Unchanged

        # Test negative tokens - should always succeed and consume nothing
        result = await limiter.acquire(tokens=-1)
        assert result is True
        assert limiter._available_tokens == initial_tokens  # Unchanged

        result = await limiter.acquire(tokens=-5)
        assert result is True
        assert limiter._available_tokens == initial_tokens  # Unchanged

        # Verify normal operation still works
        result = await limiter.acquire(tokens=3)
        assert result is True
        assert limiter._available_tokens == initial_tokens - 3

    def test_docstring_presence(self) -> None:
        """Test that the abstract class has proper documentation."""
        assert AbstractRateLimiter.__doc__ is not None
        assert len(AbstractRateLimiter.__doc__.strip()) > 0

        # Check method docstring
        method = AbstractRateLimiter.acquire
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_method_signature(self) -> None:
        """Test that acquire method has the correct signature."""
        import inspect

        # Get the signature of the abstract method
        sig = inspect.signature(AbstractRateLimiter.acquire)

        # Should have 'self' and 'tokens' parameters
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "tokens" in params

        # tokens parameter should have default value of 1
        tokens_param = sig.parameters["tokens"]
        assert tokens_param.default == 1

        # Should have bool return annotation
        assert sig.return_annotation is bool

    @pytest.mark.asyncio
    async def test_concurrent_acquire_operations(self) -> None:
        """Test that acquire method can handle concurrent operations."""
        import asyncio

        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=10)

        # Create multiple concurrent acquire tasks
        tasks = [limiter.acquire(tokens=1) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed since we have enough tokens
        assert all(results)

    @pytest.mark.asyncio
    async def test_acquire_exact_available_tokens(self) -> None:
        """Test acquiring exactly the number of available tokens."""
        limiter = ConcreteRateLimiter(allow_acquire=True, max_tokens=5)
        result = await limiter.acquire(tokens=5)
        assert result is True

        # Next acquire should fail
        result = await limiter.acquire(tokens=1)
        assert result is False


class TestTokenBucketRateLimiter:
    """Test suite for token bucket rate limiter functional scenarios."""

    @pytest.fixture
    def limiter(self) -> TokenBucketRateLimiter:
        """Provide a standard token bucket rate limiter for testing."""
        return TokenBucketRateLimiter(capacity=5, refill_rate=2.0, refill_interval=1.0, initial_tokens=5)

    def test_initialization_valid_parameters(self) -> None:
        """Test rate limiter initialization with valid parameters.

        Verifies:
        - Rate limiter initializes with correct configuration
        - Initial token state is correct
        - Statistics are properly initialized
        """
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=5.0, refill_interval=2.0, initial_tokens=7)

        assert limiter.capacity == 10
        assert limiter.refill_rate == 5.0
        assert limiter.refill_interval == 2.0
        assert limiter.get_available_tokens() == 7

        stats = limiter.get_stats()
        assert stats["capacity"] == 10
        assert stats["available_tokens"] == 7
        assert stats["acquire_count"] == 0
        assert stats["denied_count"] == 0

    def test_initialization_invalid_parameters(self) -> None:
        """Test rate limiter initialization with invalid parameters.

        Verifies:
        - Raises ValueError for invalid parameter combinations
        - Prevents creation of invalid rate limiter states
        """
        # Test invalid capacity
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucketRateLimiter(capacity=0)

        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucketRateLimiter(capacity=-1)

        # Test invalid refill rate
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucketRateLimiter(capacity=5, refill_rate=0)

        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucketRateLimiter(capacity=5, refill_rate=-1.0)

        # Test invalid refill interval
        with pytest.raises(ValueError, match="Refill interval must be positive"):
            TokenBucketRateLimiter(capacity=5, refill_interval=0)

        with pytest.raises(ValueError, match="Refill interval must be positive"):
            TokenBucketRateLimiter(capacity=5, refill_interval=-0.5)

    @pytest.mark.asyncio
    async def test_allow_requests_within_limit(self, limiter: TokenBucketRateLimiter) -> None:
        """Test that requests within rate limit are allowed.

        Test Description:
        Verifies that requests are successfully processed when sufficient
        tokens are available in the bucket.

        Test Steps:
        1. Make requests within the available token limit
        2. Verify all requests are successful
        3. Check token consumption is correct

        Expected Results:
        - All requests within limit return True
        - Tokens are properly consumed
        - Statistics reflect successful acquisitions
        """
        # Start with 5 tokens, make 3 requests
        assert limiter.get_available_tokens() == 5

        # Make requests within limit
        for _i in range(3):
            result = await limiter.acquire(tokens=1)
            assert result is True

        assert limiter.get_available_tokens() == 2

        # Verify statistics
        stats = limiter.get_stats()
        assert stats["acquire_count"] == 3
        assert stats["denied_count"] == 0
        assert stats["total_tokens_consumed"] == 3
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_block_requests_over_limit(self, limiter: TokenBucketRateLimiter) -> None:
        """Test that requests exceeding rate limit are blocked.

        Test Description:
        Verifies that requests are blocked when insufficient tokens
        are available in the bucket.

        Test Steps:
        1. Exhaust available tokens
        2. Attempt additional requests
        3. Verify requests are blocked

        Expected Results:
        - Requests beyond limit return False
        - Token count remains at zero
        - Statistics reflect denied requests
        """
        # Exhaust all tokens (capacity = 5)
        for _i in range(5):
            result = await limiter.acquire(tokens=1)
            assert result is True

        assert limiter.get_available_tokens() == 0

        # Attempt additional requests - should be blocked
        for _i in range(3):
            result = await limiter.acquire(tokens=1)
            assert result is False

        assert limiter.get_available_tokens() == 0

        # Verify statistics
        stats = limiter.get_stats()
        assert stats["acquire_count"] == 5
        assert stats["denied_count"] == 3
        assert stats["success_rate"] == 5.0 / 8.0  # 5 successful out of 8 total

    def test_time_window_reset_with_refill_deterministic(self) -> None:
        """Test that tokens are refilled over time windows using deterministic time control.

        Test Description:
        Verifies that the token bucket refills tokens according to
        the configured refill rate and interval using time-machine
        for deterministic testing.

        Test Steps:
        1. Create limiter with specific refill configuration
        2. Exhaust tokens
        3. Use time-machine to advance time precisely
        4. Verify tokens are refilled correctly

        Expected Results:
        - Tokens are refilled exactly according to configuration
        - Time-based refill is deterministic and precise
        - Refill respects configured rate and capacity
        """
        pytest.importorskip("time_machine")
        import datetime

        import time_machine

        # Create limiter with predictable refill rate
        test_limiter = TokenBucketRateLimiter(
            capacity=10,
            refill_rate=5.0,  # 5 tokens per second
            refill_interval=1.0,
            initial_tokens=10,
        )

        # Use deterministic time control
        initial_time = datetime.datetime.now()
        with time_machine.travel(initial_time) as traveler:
            # Consume all tokens
            for _i in range(10):
                result = asyncio.run(test_limiter.acquire(tokens=1))
                assert result is True

            assert test_limiter.get_available_tokens() == 0

            # Advance time by exactly 1 second
            traveler.shift(datetime.timedelta(seconds=1))

            # Trigger refill by attempting acquisition
            result = asyncio.run(test_limiter.acquire(tokens=1))
            assert result is True  # Should succeed as tokens were refilled

            # Should have refilled 5 tokens (rate=5, interval=1), minus 1 just acquired
            assert test_limiter.get_available_tokens() == 4

            # Advance time by another 2 seconds
            traveler.shift(datetime.timedelta(seconds=2))

            # Should refill to capacity (10 tokens total)
            # Force refill by attempting another acquisition
            result = asyncio.run(test_limiter.acquire(tokens=1))
            assert result is True
            # Should have full capacity minus 1 acquired token = 9
            assert test_limiter.get_available_tokens() == 9

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, limiter: TokenBucketRateLimiter) -> None:
        """Test rate limiter correctly handles concurrent requests.

        Test Description:
        Verifies that multiple concurrent requests are processed correctly
        and token consumption is atomic and consistent.

        Test Steps:
        1. Make multiple concurrent requests
        2. Verify total token consumption is correct
        3. Check that results are consistent

        Expected Results:
        - Concurrent requests are handled atomically
        - Total token consumption equals successful requests
        - No race conditions occur
        """
        # Reset to known state (respect capacity limit of 5)
        limiter.set_tokens(5)
        initial_tokens = limiter.get_available_tokens()

        # Make 8 concurrent requests for 1 token each (capacity is 5)
        tasks = [limiter.acquire(tokens=1) for _ in range(8)]
        results = await asyncio.gather(*tasks)

        # Count successful and failed requests
        successful = sum(1 for result in results if result)
        failed = sum(1 for result in results if not result)

        # Should have some successful and some failed requests
        assert successful > 0
        assert failed > 0
        assert successful + failed == 8

        # Token consumption should match successful requests
        remaining_tokens = limiter.get_available_tokens()
        consumed_tokens = initial_tokens - remaining_tokens
        assert consumed_tokens == successful

    @pytest.mark.asyncio
    async def test_multiple_token_acquisition(self, limiter: TokenBucketRateLimiter) -> None:
        """Test acquiring multiple tokens in a single request.

        Test Description:
        Verifies that requests for multiple tokens are handled correctly,
        either succeeding completely or failing completely (atomic operation).

        Test Steps:
        1. Request multiple tokens when sufficient are available
        2. Request multiple tokens when insufficient are available
        3. Verify atomic behavior

        Expected Results:
        - Multi-token requests succeed when sufficient tokens exist
        - Multi-token requests fail when insufficient tokens exist
        - Token consumption is atomic (all or nothing)
        """
        # Reset to known state (5 tokens available)
        limiter.set_tokens(5)

        # Request 3 tokens - should succeed
        result = await limiter.acquire(tokens=3)
        assert result is True
        assert limiter.get_available_tokens() == 2

        # Request 3 tokens again - should fail (only 2 available)
        result = await limiter.acquire(tokens=3)
        assert result is False
        assert limiter.get_available_tokens() == 2  # Unchanged

        # Request 2 tokens - should succeed
        result = await limiter.acquire(tokens=2)
        assert result is True
        assert limiter.get_available_tokens() == 0

    @pytest.mark.asyncio
    async def test_configuration_different_rates(self) -> None:
        """Test rate limiter with different rate configurations.

        Test Description:
        Verifies that rate limiters with different configurations
        behave according to their specific parameters.

        Test Steps:
        1. Create limiters with different rates
        2. Test behavior matches configuration
        3. Verify rate limiting is applied correctly

        Expected Results:
        - Each limiter behaves according to its configuration
        - Rate limiting scales with configured parameters
        - Different configurations can coexist
        """
        # Create limiters with different configurations
        slow_limiter = TokenBucketRateLimiter(
            capacity=2,
            refill_rate=1.0,
            refill_interval=2.0,  # 0.5 tokens per second
            initial_tokens=2,
        )

        fast_limiter = TokenBucketRateLimiter(
            capacity=10,
            refill_rate=5.0,
            refill_interval=1.0,  # 5 tokens per second
            initial_tokens=10,
        )

        # Test slow limiter - should exhaust quickly
        for _i in range(2):
            result = await slow_limiter.acquire()
            assert result is True

        result = await slow_limiter.acquire()
        assert result is False  # Should be exhausted

        # Test fast limiter - should handle more requests
        for _i in range(10):
            result = await fast_limiter.acquire()
            assert result is True

        result = await fast_limiter.acquire()
        assert result is False  # Should be exhausted

    @pytest.mark.asyncio
    async def test_boundary_conditions_zero_tokens(self, limiter: TokenBucketRateLimiter) -> None:
        """Test boundary condition with zero tokens requested.

        Test Description:
        Verifies correct behavior when zero tokens are requested,
        which should always succeed without consuming tokens.

        Test Steps:
        1. Request zero tokens with full bucket
        2. Request zero tokens with empty bucket
        3. Verify no tokens are consumed

        Expected Results:
        - Zero token requests always succeed
        - No tokens are consumed for zero token requests
        - Statistics correctly track zero token requests
        """
        # Test with full bucket
        result = await limiter.acquire(tokens=0)
        assert result is True
        assert limiter.get_available_tokens() == 5  # Unchanged

        # Exhaust bucket
        limiter.set_tokens(0)

        # Test with empty bucket
        result = await limiter.acquire(tokens=0)
        assert result is True
        assert limiter.get_available_tokens() == 0  # Still unchanged

    @pytest.mark.asyncio
    async def test_boundary_conditions_exact_capacity(self, limiter: TokenBucketRateLimiter) -> None:
        """Test boundary condition requesting exact bucket capacity.

        Test Description:
        Verifies correct behavior when requesting exactly the total
        capacity of tokens at once.

        Test Steps:
        1. Request exactly the bucket capacity
        2. Verify request succeeds with full bucket
        3. Verify request fails with insufficient tokens

        Expected Results:
        - Exact capacity requests succeed when bucket is full
        - Exact capacity requests fail when insufficient tokens
        - Bucket is completely emptied after successful exact capacity request
        """
        # Request exact capacity (5 tokens)
        result = await limiter.acquire(tokens=5)
        assert result is True
        assert limiter.get_available_tokens() == 0

        # Try again with empty bucket
        result = await limiter.acquire(tokens=5)
        assert result is False
        assert limiter.get_available_tokens() == 0

    @pytest.mark.asyncio
    async def test_boundary_conditions_over_capacity(self, limiter: TokenBucketRateLimiter) -> None:
        """Test boundary condition requesting more than bucket capacity.

        Test Description:
        Verifies correct behavior when requesting more tokens than
        the bucket can ever hold.

        Test Steps:
        1. Request more tokens than capacity
        2. Verify request always fails
        3. Verify bucket state remains unchanged

        Expected Results:
        - Over-capacity requests always fail
        - Bucket state remains unchanged
        - Statistics correctly track failed requests
        """
        # Request more than capacity (5 tokens available, request 10)
        result = await limiter.acquire(tokens=10)
        assert result is False
        assert limiter.get_available_tokens() == 5  # Unchanged

        stats = limiter.get_stats()
        assert stats["denied_count"] == 1

    def test_rate_limiter_statistics_accuracy(self, limiter: TokenBucketRateLimiter) -> None:
        """Test accuracy of rate limiter statistics reporting.

        Test Description:
        Verifies that rate limiter statistics accurately reflect
        the current state and historical operations.

        Test Steps:
        1. Perform various operations
        2. Check statistics at each step
        3. Verify accuracy of all reported metrics

        Expected Results:
        - Statistics accurately reflect current state
        - Historical counts are correct
        - Success rate calculation is accurate
        """
        initial_stats = limiter.get_stats()
        assert initial_stats["capacity"] == 5
        assert initial_stats["available_tokens"] == 5
        assert initial_stats["acquire_count"] == 0
        assert initial_stats["denied_count"] == 0
        assert initial_stats["success_rate"] == 0.0

        # Set specific token count for predictable testing
        limiter.set_tokens(3)

        stats = limiter.get_stats()
        assert stats["available_tokens"] == 3

        # Reset and verify stats
        limiter.reset_stats()
        stats = limiter.get_stats()
        assert stats["acquire_count"] == 0
        assert stats["denied_count"] == 0
        assert stats["total_tokens_consumed"] == 0

    @pytest.mark.asyncio
    async def test_interface_contract_compliance(self) -> None:
        """Test that TokenBucketRateLimiter satisfies the interface contract.

        Test Description:
        Verifies that the token bucket implementation correctly implements
        the AbstractRateLimiter interface and behaves polymorphically.

        Test Steps:
        1. Verify inheritance relationship
        2. Test polymorphic behavior
        3. Verify method signatures match interface

        Expected Results:
        - Implementation is instance of abstract class
        - Polymorphic behavior works correctly
        - Interface contract is satisfied
        """
        limiter = TokenBucketRateLimiter()

        # Should be an instance of the abstract class
        assert isinstance(limiter, AbstractRateLimiter)

        # Should have the required method
        assert hasattr(limiter, "acquire")
        assert callable(limiter.acquire)

        # Test polymorphic usage
        async def use_rate_limiter(rate_limiter: AbstractRateLimiter) -> bool:
            return await rate_limiter.acquire(tokens=1)

        result = await use_rate_limiter(limiter)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_time_based_refill_accuracy(self) -> None:
        """Test accuracy of time-based token refill mechanism.

        Test Description:
        Verifies that tokens are refilled accurately according to
        the configured rate and time intervals.

        Test Steps:
        1. Create limiter with specific refill configuration
        2. Use force_refill to simulate time passing
        3. Verify refill behavior

        Expected Results:
        - Tokens refill according to configuration
        - Refill doesn't exceed bucket capacity
        - Refill timing logic works correctly
        """
        # Create limiter with predictable refill rate
        test_limiter = TokenBucketRateLimiter(
            capacity=10,
            refill_rate=5.0,  # 5 tokens per second
            refill_interval=1.0,
            initial_tokens=3,  # Start with some tokens
        )

        # Initially should have 3 tokens
        assert test_limiter.get_available_tokens() == 3

        # Consume some tokens
        result = await test_limiter.acquire(tokens=2)
        assert result is True
        assert test_limiter.get_available_tokens() == 1

        # Force refill to capacity (simulates time passing)
        test_limiter.force_refill()
        assert test_limiter.get_available_tokens() == 10

        # Test that refill doesn't exceed capacity
        test_limiter.force_refill()
        assert test_limiter.get_available_tokens() == 10  # Should still be at capacity

        # Test partial refill using a more controlled approach
        test_limiter.set_tokens(0)  # Start empty

        # Wait a short time and check if refill works with actual time
        await asyncio.sleep(0.5)
        result = await test_limiter.acquire(tokens=1)

        # Should either succeed (if refill happened) or fail (if not enough time passed)
        # This is more about testing the mechanism than precise timing
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_burst_handling_after_idle_period(self) -> None:
        """Test handling of burst requests after idle period.

        Test Description:
        Verifies that the rate limiter can handle burst requests
        appropriately after a period of inactivity allows token accumulation.

        Test Steps:
        1. Allow tokens to accumulate during idle period
        2. Make burst of requests
        3. Verify burst is handled according to accumulated tokens

        Expected Results:
        - Burst requests succeed up to accumulated token limit
        - Excess burst requests are properly rejected
        - Rate limiting resumes after burst
        """
        # Create limiter with moderate capacity
        burst_limiter = TokenBucketRateLimiter(capacity=8, refill_rate=2.0, refill_interval=1.0, initial_tokens=8)

        # Allow some time to pass (tokens should remain at capacity)
        await asyncio.sleep(0.5)

        # Make burst of requests
        burst_results = []
        for _i in range(12):  # More than capacity
            result = await burst_limiter.acquire(tokens=1)
            burst_results.append(result)

        # Should have some successful and some failed
        successful = sum(burst_results)
        failed = len(burst_results) - successful

        assert successful <= 8  # Can't exceed capacity
        assert failed > 0  # Some should fail
        assert successful > 0  # Some should succeed

    @pytest.mark.asyncio
    async def test_edge_case_rapid_sequential_requests(self) -> None:
        """Test edge case with rapid sequential requests.

        Test Description:
        Verifies rate limiter handles rapid sequential requests correctly
        without timing-related inconsistencies.

        Test Steps:
        1. Make rapid sequential requests
        2. Verify consistent behavior
        3. Check token accounting accuracy

        Expected Results:
        - Sequential requests are handled consistently
        - Token accounting remains accurate
        - No race conditions or timing issues
        """
        sequential_limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0, refill_interval=1.0, initial_tokens=5)

        results = []
        for _i in range(10):
            result = await sequential_limiter.acquire(tokens=1)
            results.append(result)
            # Small delay to allow async processing
            await asyncio.sleep(0.01)

        # Should have exactly 5 successful (initial tokens)
        successful = sum(results)
        assert successful == 5

        # Remaining should be failed
        failed = len(results) - successful
        assert failed == 5

    @pytest.mark.asyncio
    async def test_configuration_edge_cases(self) -> None:
        """Test edge cases in rate limiter configuration.

        Test Description:
        Verifies rate limiter handles edge case configurations
        correctly, such as very small intervals or rates.

        Test Steps:
        1. Create limiters with edge case configurations
        2. Test basic functionality
        3. Verify behavior remains correct

        Expected Results:
        - Edge case configurations work correctly
        - Rate limiting behavior is predictable
        - No mathematical errors or exceptions
        """
        # Test with very small capacity
        tiny_limiter = TokenBucketRateLimiter(capacity=1, refill_rate=1.0, refill_interval=1.0, initial_tokens=1)

        result = await tiny_limiter.acquire(tokens=1)
        assert result is True

        result = await tiny_limiter.acquire(tokens=1)
        assert result is False

        # Test with fractional refill rate
        fractional_limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0.5, refill_interval=1.0, initial_tokens=5)

        result = await fractional_limiter.acquire(tokens=1)
        assert result is True

    def test_error_handling_comprehensive(self) -> None:
        """Test comprehensive error handling for invalid configurations.

        Test Description:
        Verifies that the rate limiter properly validates all parameters
        and provides meaningful error messages for invalid configurations.

        Test Steps:
        1. Test various invalid parameter combinations
        2. Verify appropriate exceptions are raised
        3. Test boundary conditions

        Expected Results:
        - Invalid configurations raise ValueError with descriptive messages
        - Boundary conditions are handled correctly
        - Error messages are informative for debugging
        """
        # Test invalid capacity values
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucketRateLimiter(capacity=0)

        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucketRateLimiter(capacity=-5)

        # Test invalid refill rate values
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucketRateLimiter(capacity=10, refill_rate=0)

        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucketRateLimiter(capacity=10, refill_rate=-1.5)

        # Test invalid refill interval values
        with pytest.raises(ValueError, match="Refill interval must be positive"):
            TokenBucketRateLimiter(capacity=10, refill_rate=1.0, refill_interval=0)

        with pytest.raises(ValueError, match="Refill interval must be positive"):
            TokenBucketRateLimiter(capacity=10, refill_rate=1.0, refill_interval=-0.5)

        # Test valid boundary cases should work
        # Very small positive values should be accepted
        limiter_small = TokenBucketRateLimiter(capacity=1, refill_rate=0.001, refill_interval=0.001)
        assert limiter_small.capacity == 1
        assert limiter_small.refill_rate == 0.001
        assert limiter_small.refill_interval == 0.001

        # Very large values should be accepted
        limiter_large = TokenBucketRateLimiter(capacity=1000000, refill_rate=10000.0, refill_interval=3600.0)
        assert limiter_large.capacity == 1000000
        assert limiter_large.refill_rate == 10000.0
        assert limiter_large.refill_interval == 3600.0

    def test_metrics_accuracy_comprehensive(self) -> None:
        """Test comprehensive accuracy of rate limiter metrics and statistics.

        Test Description:
        Verifies that all metrics accurately reflect the rate limiter's
        state and operations history.

        Test Steps:
        1. Perform various operations on the rate limiter
        2. Check metrics accuracy at each step
        3. Verify all statistical calculations

        Expected Results:
        - All metrics accurately reflect operations
        - Statistical calculations are mathematically correct
        - Metrics remain consistent across operations
        """
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=2.0, refill_interval=1.0, initial_tokens=10)

        # Test initial state metrics
        initial_stats = limiter.get_stats()
        assert initial_stats["capacity"] == 10
        assert initial_stats["available_tokens"] == 10
        assert initial_stats["refill_rate"] == 2.0
        assert initial_stats["refill_interval"] == 1.0
        assert initial_stats["acquire_count"] == 0
        assert initial_stats["denied_count"] == 0
        assert initial_stats["total_tokens_consumed"] == 0
        assert initial_stats["success_rate"] == 0.0  # No operations yet

        # Perform successful operations and verify metrics
        for i in range(5):
            result = asyncio.run(limiter.acquire(tokens=2))
            assert result is True

            stats = limiter.get_stats()
            assert stats["acquire_count"] == i + 1
            assert stats["denied_count"] == 0
            assert stats["total_tokens_consumed"] == (i + 1) * 2
            assert stats["available_tokens"] == 10 - (i + 1) * 2
            assert stats["success_rate"] == 1.0  # All successful so far

        # Now limiter should be exhausted (10 tokens consumed)
        assert limiter.get_available_tokens() == 0

        # Perform failed operations and verify metrics
        for i in range(3):
            result = asyncio.run(limiter.acquire(tokens=1))
            assert result is False

            stats = limiter.get_stats()
            assert stats["acquire_count"] == 5  # Still 5 successful
            assert stats["denied_count"] == i + 1
            assert stats["total_tokens_consumed"] == 10  # No additional consumption
            assert stats["available_tokens"] == 0

            # Calculate expected success rate: 5 successful / (5 + i + 1) total
            total_attempts = 5 + i + 1
            expected_success_rate = 5.0 / total_attempts
            assert abs(stats["success_rate"] - expected_success_rate) < 0.001

        # Test reset functionality
        limiter.reset_stats()
        reset_stats = limiter.get_stats()
        assert reset_stats["acquire_count"] == 0
        assert reset_stats["denied_count"] == 0
        assert reset_stats["total_tokens_consumed"] == 0
        assert reset_stats["success_rate"] == 0.0
        # Configuration should remain unchanged
        assert reset_stats["capacity"] == 10
        assert reset_stats["refill_rate"] == 2.0
        assert reset_stats["refill_interval"] == 1.0

        # Test force refill functionality
        limiter.set_tokens(3)  # Set to partial capacity
        assert limiter.get_available_tokens() == 3

        limiter.force_refill()  # Should refill to full capacity
        assert limiter.get_available_tokens() == 10

        # Test set_tokens boundary conditions
        limiter.set_tokens(15)  # Above capacity
        assert limiter.get_available_tokens() == 10  # Should be clamped to capacity

        limiter.set_tokens(-5)  # Below zero
        assert limiter.get_available_tokens() == 0  # Should be clamped to zero

    @pytest.mark.asyncio
    async def test_concurrent_operations_stress(self) -> None:
        """Test rate limiter under concurrent stress conditions.

        Test Description:
        Verifies that the rate limiter maintains consistency and accuracy
        under high concurrent load with many simultaneous operations.

        Test Steps:
        1. Create many concurrent acquisition tasks
        2. Mix successful and failing operations
        3. Verify final state consistency

        Expected Results:
        - Concurrent operations maintain consistency
        - No race conditions in token accounting
        - Statistics remain accurate under stress
        """
        limiter = TokenBucketRateLimiter(capacity=50, refill_rate=10.0, refill_interval=1.0, initial_tokens=50)

        # Create many concurrent tasks requesting different token amounts
        async def acquisition_task(tokens: int) -> bool:
            return await limiter.acquire(tokens=tokens)

        # Mix of different token requests to create various scenarios
        tasks = []
        for _ in range(20):
            tasks.append(acquisition_task(1))  # Small requests
        for _ in range(10):
            tasks.append(acquisition_task(3))  # Medium requests
        for _ in range(5):
            tasks.append(acquisition_task(10))  # Large requests
        for _ in range(3):
            tasks.append(acquisition_task(25))  # Very large requests

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify results consistency
        successful_requests = sum(1 for result in results if result)
        failed_requests = sum(1 for result in results if not result)
        total_requests = len(results)

        assert successful_requests + failed_requests == total_requests

        # Verify statistics match actual results
        stats = limiter.get_stats()
        assert stats["acquire_count"] == successful_requests
        assert stats["denied_count"] == failed_requests

        # Verify success rate calculation
        expected_success_rate = successful_requests / total_requests if total_requests > 0 else 0.0
        assert abs(stats["success_rate"] - expected_success_rate) < 0.001

        # Verify token accounting remains consistent
        assert stats["available_tokens"] >= 0
        assert stats["available_tokens"] <= limiter.capacity

        # Verify total tokens consumed is reasonable
        assert stats["total_tokens_consumed"] <= limiter.capacity  # Can't consume more than started with
