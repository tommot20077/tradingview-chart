"""Abstract event bus interface.

This module defines the abstract base class for an event bus, providing
a standardized interface for publishing, subscribing to, and managing
events within the `asset_core` library. Implementations of this interface
facilitate decoupled communication between different components of the system.
"""

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
    """Abstract interface for an event bus implementation.

    This abstract base class defines the contract for event bus systems,
    providing methods for publishing events, subscribing to event types,
    and managing event handlers. It facilitates decoupled communication
    between different components of an application.
    """

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publishes an event to the bus, dispatching it to all relevant subscribers.

        Args:
            event: The `BaseEvent` instance to publish.

        Raises:
            EventBusError: If there is an error during event publishing.
        """

    @abstractmethod
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
        *,
        filter_symbol: str | None = None,
    ) -> str:
        """Subscribes a handler function to events of a specific type.

        The handler will be invoked whenever an event matching the `event_type`
        (and optional `filter_symbol`) is published to the bus.

        Args:
            event_type: The `EventType` to subscribe to.
            handler: The callable function (synchronous or asynchronous) that will
                     process the events. It should accept a `BaseEvent` as its sole argument.
            filter_symbol: An optional trading symbol string. If provided, the handler
                           will only receive events associated with this specific symbol.

        Returns:
            A unique string identifier for this subscription, which can be used later to unsubscribe.

        Raises:
            EventBusError: If there is an error during subscription.
        """

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribes a handler from the event bus using its subscription ID.

        Args:
            subscription_id: The unique string ID returned by the `subscribe` method.

        Returns:
            `True` if the subscription was successfully removed, `False` if the ID was not found.

        Raises:
            EventBusError: If there is an error during unsubscription.
        """

    @abstractmethod
    def unsubscribe_all(self, event_type: EventType | None = None) -> int:
        """Unsubscribes all handlers, optionally for a specific event type.

        Args:
            event_type: Optional. If provided, only handlers for this specific
                        `EventType` will be unsubscribed. If `None`, all handlers
                        for all event types will be unsubscribed.

        Returns:
            The number of handlers that were unsubscribed.

        Raises:
            EventBusError: If there is an error during the operation.
        """

    @abstractmethod
    async def close(self) -> None:
        """Closes the event bus, releasing any resources and stopping internal processes.

        This method should be called during application shutdown to ensure a clean exit.

        Raises:
            EventBusError: If there is an error during closing.
        """

    @abstractmethod
    def get_subscription_count(self, event_type: EventType | None = None) -> int:
        """Retrieves the number of active subscriptions.

        Args:
            event_type: Optional. If provided, counts subscriptions only for this
                        specific `EventType`. If `None`, counts all active subscriptions.

        Returns:
            The total number of active subscriptions matching the criteria.
        """

    @abstractmethod
    async def wait_for(
        self,
        event_type: EventType,
        *,
        timeout: float | None = None,
        filter_func: Callable[[BaseEvent], bool] | None = None,
    ) -> BaseEvent | None:
        """Waits asynchronously for a specific event to be published.

        This method blocks until an event of the specified `event_type` is received
        and optionally passes a `filter_func`.

        Args:
            event_type: The `EventType` to wait for.
            timeout: Optional. The maximum number of seconds to wait for the event.
                     If `None`, it waits indefinitely.
            filter_func: Optional. A callable that takes a `BaseEvent` and returns `True`
                         if the event matches the desired criteria, `False` otherwise.

        Returns:
            The `BaseEvent` object if received within the timeout and matching the filter,
            otherwise `None`.

        Raises:
            EventBusError: If there is an error during the wait operation.
        """

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        """Indicates whether the event bus is currently closed.

        Returns:
            `True` if the event bus is closed, `False` otherwise.
        """
