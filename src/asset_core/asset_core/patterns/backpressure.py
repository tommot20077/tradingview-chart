"""Backpressure controller interface definition."""

from abc import ABC, abstractmethod


class AbstractBackpressureController(ABC):
    """Abstract base class for backpressure controllers.

    This interface defines the contract for backpressure control implementations.
    Concrete implementations should be provided in the application layer.
    """

    @abstractmethod
    async def should_throttle(self) -> bool:
        """Check if the system should throttle requests due to backpressure.

        Returns:
            True if the system should throttle, False otherwise
        """
        pass
