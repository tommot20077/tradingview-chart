"""Rate limiter interface definition."""

from abc import ABC, abstractmethod


class AbstractRateLimiter(ABC):
    """Abstract base class for rate limiters.

    This interface defines the contract for rate limiting implementations.
    Concrete implementations should be provided in the application layer.
    """

    @abstractmethod
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the rate limiter.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens were successfully acquired, False otherwise
        """
        pass
