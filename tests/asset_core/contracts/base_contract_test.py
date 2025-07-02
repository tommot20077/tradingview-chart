"""
Base classes for contract testing.

Provides common utilities and patterns for testing abstract interfaces
and ensuring behavioral contracts are met.
"""

import asyncio
import inspect
from typing import Any, get_type_hints
from unittest.mock import AsyncMock, MagicMock

import pytest


class BaseContractTest:
    """
    Base class for all contract tests.

    Provides common utilities for testing abstract interfaces and ensuring
    that concrete implementations follow behavioral contracts.
    """

    @staticmethod
    def get_abstract_methods(cls: type) -> list[str]:
        """
        Get list of abstract method names from a class.

        Args:
            cls: The class to inspect

        Returns:
            List of abstract method names
        """
        if not hasattr(cls, "__abstractmethods__"):
            return []
        return list(cls.__abstractmethods__)

    @staticmethod
    def get_method_signature(cls: type, method_name: str) -> inspect.Signature:
        """
        Get method signature from a class.

        Args:
            cls: The class containing the method
            method_name: Name of the method

        Returns:
            Method signature
        """
        method = getattr(cls, method_name)
        return inspect.signature(method)

    @staticmethod
    def get_method_annotations(cls: type, method_name: str) -> dict[str, Any]:
        """
        Get type annotations for a method.

        Args:
            cls: The class containing the method
            method_name: Name of the method

        Returns:
            Dictionary of parameter and return type annotations
        """
        method = getattr(cls, method_name)
        return get_type_hints(method)

    @staticmethod
    def create_mock_method(is_async: bool = False, return_value: Any = None) -> Any:
        """
        Create a mock method that can be async or sync.

        Args:
            is_async: Whether the method should be async
            return_value: Value to return from the method

        Returns:
            Mock method (AsyncMock or MagicMock)
        """
        mock = AsyncMock(return_value=return_value) if is_async else MagicMock(return_value=return_value)
        return mock

    @staticmethod
    def is_async_method(cls: type, method_name: str) -> bool:
        """
        Check if a method is async.

        Args:
            cls: The class containing the method
            method_name: Name of the method

        Returns:
            True if method is async, False otherwise
        """
        method = getattr(cls, method_name)

        # Check if it's actually an async function or async generator function
        if asyncio.iscoroutinefunction(method) or inspect.isasyncgenfunction(method):
            return True

        # Check if it returns an AsyncIterator or AsyncGenerator (for abstract methods)
        try:
            from collections.abc import AsyncGenerator, AsyncIterator

            type_hints = get_type_hints(method)
            return_type = type_hints.get("return")
            if return_type:
                # Handle parameterized generics like AsyncIterator[Trade]
                origin = getattr(return_type, "__origin__", return_type)
                return origin in (AsyncIterator, AsyncGenerator)
        except (NameError, AttributeError, TypeError):
            pass

        return False

    @staticmethod
    def has_async_context_manager(cls: type) -> bool:
        """
        Check if class implements async context manager protocol.

        Args:
            cls: The class to check

        Returns:
            True if class has __aenter__ and __aexit__ methods
        """
        return (
            hasattr(cls, "__aenter__")
            and hasattr(cls, "__aexit__")
            and callable(cls.__aenter__)
            and callable(cls.__aexit__)
        )


class AsyncContractTestMixin:
    """
    Mixin for async contract tests.

    Provides utilities for testing async context managers and async methods.
    """

    async def assert_async_context_manager_protocol(self, instance: Any) -> None:
        """
        Assert that an instance properly implements async context manager protocol.

        Tests that __aenter__ and __aexit__ work correctly and that the
        context manager returns the expected value.

        Args:
            instance: Instance to test
        """
        # Test that we can enter the context manager
        async with instance as ctx:
            # Context manager should typically return self
            assert ctx is instance or ctx is not None

        # Test explicit __aenter__ and __aexit__ calls
        entered = await instance.__aenter__()
        assert entered is instance or entered is not None

        # Test __aexit__ with no exception
        result = await instance.__aexit__(None, None, None)
        # __aexit__ should return None or False (don't suppress exceptions)
        assert result is None or result is False

    async def assert_method_raises_when_not_ready(
        self, instance: Any, method_name: str, exception_type: type[Exception], *args: Any, **kwargs: Any
    ) -> None:
        """
        Assert that a method raises an exception when the instance is not ready.

        Useful for testing that methods fail appropriately when preconditions
        are not met (e.g., not connected, not initialized).

        Args:
            instance: Instance to test
            method_name: Name of method to call
            exception_type: Expected exception type
            *args: Arguments to pass to method
            **kwargs: Keyword arguments to pass to method
        """
        import inspect

        method = getattr(instance, method_name)
        with pytest.raises(exception_type):
            if inspect.isasyncgenfunction(method):
                # For async generators, we need to create the generator and get the first item
                async_gen = method(*args, **kwargs)
                await async_gen.__anext__()
            elif asyncio.iscoroutinefunction(method):
                await method(*args, **kwargs)
            else:
                method(*args, **kwargs)


class MockImplementationBase:
    """
    Base class for creating mock implementations of abstract interfaces.

    Provides common patterns for implementing mock classes that can be used
    in contract tests.
    """

    def __init__(self) -> None:
        self._is_connected = False
        self._is_closed = False

    @property
    def is_connected(self) -> bool:
        """Mock connection status."""
        return self._is_connected

    @property
    def is_closed(self) -> bool:
        """Mock closed status."""
        return self._is_closed

    def _check_connected(self) -> None:
        """Check if connected, raise if not."""
        if not self._is_connected:
            raise RuntimeError("Not connected")

    def _check_not_closed(self) -> None:
        """Check if not closed, raise if closed."""
        if self._is_closed:
            raise RuntimeError("Already closed")
