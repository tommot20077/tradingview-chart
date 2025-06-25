#!/usr/bin/env python3
"""
Example demonstrating comprehensive trace ID functionality.

This example shows how trace IDs are automatically propagated through:
- Logging system
- Exception handling
- Async operations
- HTTP middleware (simulated)
"""

import asyncio
from datetime import datetime

from src.asset_core.asset_core.exceptions import (
    CoreError,
    DataValidationError,
    install_global_exception_handler,
    uninstall_global_exception_handler,
)
from src.asset_core.asset_core.observability.logging import (
    TraceableLogger,
    log_exception_with_context,
    setup_logging,
)
from src.asset_core.asset_core.observability.trace_id import (
    TraceContext,
    TraceIdMiddleware,
    ensure_trace_id,
    get_formatted_trace_id,
    get_trace_id,
    set_trace_id,
    with_trace_id,
)


def setup_example_logging():
    """Setup logging for the example."""
    setup_logging(
        level="INFO",
        enable_console=True,
        enable_file=False,
        console_format="PRETTY",
    )


class DataProcessor:
    """Example service that processes data with trace ID tracking."""

    def __init__(self):
        self.logger = TraceableLogger("DataProcessor", service="example")

    def process_data(self, data: dict) -> dict:
        """Process data with comprehensive logging and error handling."""
        self.logger.info(f"Starting data processing for {len(data)} items")

        try:
            # Simulate validation
            if not data.get("valid"):
                raise DataValidationError("Data validation failed", field_name="valid", field_value=data.get("valid"))

            # Simulate processing
            result = {"processed": True, "item_count": len(data), "timestamp": datetime.now().isoformat()}

            self.logger.info(f"Data processing completed successfully: {result}")
            return result

        except Exception as e:
            self.logger.error("Data processing failed", exc=e)
            raise


class ApiServer:
    """Simulated API server with trace ID middleware."""

    def __init__(self):
        self.middleware = TraceIdMiddleware()
        self.data_processor = DataProcessor()
        self.logger = TraceableLogger("ApiServer", service="api")

    def handle_request(self, headers: dict, payload: dict) -> dict:
        """Handle API request with trace ID extraction."""
        # Extract trace ID from headers or create new one
        trace_id = self.middleware.extract_trace_id(headers)
        if not trace_id:
            trace_id = ensure_trace_id()
            self.logger.info("Created new trace ID for request")
        else:
            set_trace_id(trace_id)
            self.logger.info(f"Using trace ID from headers: {trace_id}")

        try:
            # Process the request
            result = self.data_processor.process_data(payload)

            # Add trace ID to response headers
            response_headers = self.middleware.inject_trace_id({"Content-Type": "application/json"})

            return {"data": result, "headers": response_headers, "trace_id": get_formatted_trace_id()}

        except Exception as e:
            # Log the exception with context
            log_exception_with_context(e, "ERROR", "Request processing failed")
            raise


@with_trace_id()
async def async_operation(data: str) -> str:
    """Example async operation that maintains trace ID context."""
    logger = TraceableLogger("AsyncWorker")
    logger.info(f"Starting async operation with data: {data}")

    # Simulate async work
    await asyncio.sleep(0.1)

    if data == "error":
        raise CoreError("Simulated async error", error_code="ASYNC_ERROR")

    result = f"Processed: {data}"
    logger.info(f"Async operation completed: {result}")
    return result


async def concurrent_operations():
    """Demonstrate trace ID isolation in concurrent operations."""
    logger = TraceableLogger("ConcurrentDemo")

    async def worker(worker_id: int, should_error: bool = False):
        with TraceContext(f"worker_{worker_id}"):
            logger.info(f"Worker {worker_id} starting")
            if should_error:
                try:
                    await async_operation("error")
                except CoreError as e:
                    logger.error(f"Worker {worker_id} encountered error", exc=e)
                    return f"Worker {worker_id} failed"
            else:
                result = await async_operation(f"data_{worker_id}")
                return f"Worker {worker_id}: {result}"

    # Run multiple workers concurrently
    logger.info("Starting concurrent operations")
    tasks = [worker(i, should_error=(i == 2)) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Task {i} failed with exception: {result}")
        else:
            logger.info(f"Task {i} result: {result}")


def demonstrate_exception_handling():
    """Demonstrate exception handling with trace IDs."""
    logger = TraceableLogger("ExceptionDemo")

    # Install global exception handler
    install_global_exception_handler()

    try:
        with TraceContext("exception_demo"):
            logger.info("Demonstrating exception handling")

            # Create a nested exception scenario
            try:
                # This will raise with trace ID
                raise DataValidationError("Invalid input data", field_name="test", field_value=None)
            except DataValidationError as e:
                # Log the exception with context
                log_exception_with_context(e, "WARNING", "Validation failed, retrying with defaults")

                # Create another exception that chains from this one
                raise CoreError("Processing failed after validation error") from e

    except CoreError as e:
        logger.error("Final exception caught", exc=e)
        print(f"\nFinal exception trace ID: {e.trace_id}")
        print(f"Exception string representation: {e}")
        print(f"Exception repr: {repr(e)}")

    finally:
        uninstall_global_exception_handler()


def simulate_http_requests():
    """Simulate HTTP requests with trace ID propagation."""
    api_server = ApiServer()
    logger = TraceableLogger("HTTPDemo")

    requests = [
        {"headers": {}, "payload": {"valid": True, "item1": "data1", "item2": "data2"}},
        {"headers": {"X-Trace-Id": "external_trace_123"}, "payload": {"valid": True, "data": "test"}},
        {"headers": {}, "payload": {"valid": False, "invalid_data": True}},  # This will fail
    ]

    for i, request in enumerate(requests):
        logger.info(f"Processing HTTP request {i + 1}")

        try:
            with TraceContext():  # Each request gets its own context
                response = api_server.handle_request(request["headers"], request["payload"])
                logger.info(f"Request {i + 1} successful", response_trace_id=response["trace_id"])

        except Exception as e:
            logger.error(f"Request {i + 1} failed", exc=e)

        print()  # Add spacing between requests


async def main():
    """Main example function."""
    print("🔍 Comprehensive Trace ID System Demo")
    print("=" * 50)

    # Setup logging
    setup_example_logging()

    with TraceContext("main_demo"):
        logger = TraceableLogger("MainDemo", version="1.0.0")
        logger.info("Starting comprehensive trace ID demonstration")

        print("\n1. 📡 HTTP Request Simulation")
        print("-" * 30)
        simulate_http_requests()

        print("\n2. 🔄 Concurrent Operations Demo")
        print("-" * 30)
        await concurrent_operations()

        print("\n3. ⚠️  Exception Handling Demo")
        print("-" * 30)
        demonstrate_exception_handling()

        print("\n4. 🧪 Manual Trace ID Operations")
        print("-" * 30)

        # Demonstrate manual trace ID operations
        logger.info("Demonstrating manual trace ID operations")

        original_trace = get_trace_id()
        logger.info(f"Original trace ID: {original_trace}")

        # Set a custom trace ID
        set_trace_id("custom_trace_demo")
        logger.info(f"Custom trace ID set: {get_trace_id()}")

        # Use context manager
        with TraceContext("nested_context"):
            logger.info(f"Nested context trace ID: {get_trace_id()}")

        logger.info(f"Back to previous trace ID: {get_trace_id()}")

        logger.info("Demo completed successfully! 🎉")


if __name__ == "__main__":
    asyncio.run(main())
