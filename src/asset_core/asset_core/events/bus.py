"""Abstract event bus interface."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

from ..models import BaseEvent
from ..models.events import EventType

T = TypeVar("T", bound=BaseEvent)
EventHandler = Callable[[BaseEvent], None]
AsyncEventHandler = Callable[[BaseEvent], asyncio.Future[None]]


class AbstractEventBus(ABC):
    """Abstract interface for event bus implementations."""

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to the bus.

        Args:
            event: Event to publish
        """
        pass

    @abstractmethod
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            handler: Function to handle events
            filter_symbol: Optional symbol filter

        Returns:
            Subscription ID that can be used to unsubscribe
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID returned from subscribe()

        Returns:
            True if successfully unsubscribed, False if subscription not found
        """
        pass

    @abstractmethod
    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Unsubscribe all handlers.

        Args:
            event_type: Optional event type to unsubscribe from.
                       If None, unsubscribe from all events.

        Returns:
            Number of handlers unsubscribed
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the event bus and clean up resources."""
        pass

    @abstractmethod
    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Get number of active subscriptions.

        Args:
            event_type: Optional event type to count.
                       If None, count all subscriptions.

        Returns:
            Number of active subscriptions
        """
        pass

    @abstractmethod
    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,
        filter_func: Callable[[BaseEvent], bool] | None = None,
    ) -> BaseEvent | None:
        """Wait for a specific event.

        Args:
            event_type: Type of event to wait for
            timeout: Optional timeout in seconds
            filter_func: Optional function to filter events

        Returns:
            Event if received within timeout, None otherwise
        """
        pass

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        """Check if the event bus is closed."""
        pass
