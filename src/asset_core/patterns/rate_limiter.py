"""Rate limiter interface definition.

This module defines the abstract base class for rate limiters. Rate limiting
is a crucial mechanism for controlling the rate at which a client or user
can send requests to a server or access a resource, preventing abuse and
ensuring fair usage.
"""

from abc import ABC, abstractmethod


class AbstractRateLimiter(ABC):
    """Abstract base class for implementing rate limiting.

    Rate limiting is essential for controlling the rate at which requests
    are processed, preventing system overload and ensuring fair resource usage.
    This interface defines the core method for acquiring tokens to proceed with an operation.
    """

    @abstractmethod
    async def acquire(self, tokens: int = 1) -> bool:
        """Attempts to acquire a specified number of tokens from the rate limiter.

        This method is typically called before performing an action that is subject
        to rate limits. If tokens cannot be acquired, the caller should wait or
        handle the rate limit exhaustion.

        Args:
            tokens: The number of tokens to acquire. Defaults to 1.

        Returns:
            `True` if the tokens were successfully acquired, `False` otherwise.
        """
        pass
