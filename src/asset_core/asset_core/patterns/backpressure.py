"""Backpressure controller interface definition.

This module defines the abstract base class for backpressure controllers.
Backpressure mechanisms are crucial for preventing system overload by regulating
the flow of data or requests when downstream components are unable to process
them at the incoming rate.
"""

from abc import ABC, abstractmethod


class AbstractBackpressureController(ABC):
    """Abstract base class for implementing backpressure control.

    Backpressure is a mechanism to prevent system overload by regulating the
    flow of data or requests when downstream components are unable to process
    them at the incoming rate. This interface defines the core method for
    determining if throttling is necessary.
    """

    @abstractmethod
    async def should_throttle(self) -> bool:
        """Determines if the system should apply throttling due to backpressure.

        This method is called by producers to check if they should pause or slow
        down their operations to prevent overwhelming consumers.

        Returns:
            `True` if throttling is advised, `False` otherwise.
        """
        pass
