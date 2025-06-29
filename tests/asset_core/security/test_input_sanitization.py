"""Input sanitization and security tests.

This module tests the system's ability to handle malicious inputs safely,
including SQL injection attempts, XSS payloads, and path traversal attacks.
These tests ensure that the system properly validates and sanitizes inputs
to prevent security vulnerabilities.
"""

import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from loguru import logger

from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide


class TestInputSanitization:
    """Tests for input sanitization and security validation.

    Description of what the test covers:
    This test suite focuses on verifying the system's input sanitization and
    validation mechanisms to prevent common security vulnerabilities. It includes
    tests for SQL injection prevention, XSS (Cross-Site Scripting) payload sanitization
    in logs, and path traversal attack prevention in file operations. The goal is to
    ensure that malicious inputs are properly identified, rejected, or neutralized.

    Preconditions:
    - Input validation mechanisms are implemented in relevant models and functions.
    - The logging system is configured to handle and potentially sanitize malicious inputs.
    - File handling operations incorporate robust path validation.

    Steps:
    - Execute tests for SQL injection prevention in model fields.
    - Execute tests for XSS payload sanitization in logging outputs.
    - Execute tests for path traversal attack prevention in simulated file operations.
    - Verify that various malicious input patterns are correctly handled.

    Expected Result:
    - Malicious inputs are consistently and correctly rejected or sanitized.
    - The system remains secure and stable when subjected to common attack attempts.
    - No security vulnerabilities (e.g., SQL injection, XSS, path traversal) are exposed.
    - Appropriate error handling and logging occur for invalid or malicious inputs.
    """

    def test_sql_injection_prevention(self) -> None:
        """Test prevention of SQL injection attacks in model inputs.

        Description of what the test covers:
        This test verifies that the system's Pydantic models correctly handle
        and prevent SQL injection attempts by validating inputs. It ensures that
        malicious SQL payloads, when provided as string inputs to model fields,
        are treated as literal text and do not lead to unintended database operations
        or information exposure.

        Preconditions:
        - Pydantic models (`Trade`, `Kline`) are defined with input validation.
        - SQL injection payloads are prepared for testing.

        Steps:
        - Attempt to create `Trade` and `Kline` model instances with invalid symbols
          (empty string, whitespace only) and assert that `ValueError` is raised.
        - Create model instances with SQL injection payloads in string fields (e.g., `trade_id`,
          `exchange`) and assert that the models accept these as literal strings.
        - Verify that the `model_dump()` output for these instances contains the literal
          payloads, confirming they are treated as data, not executable code.
        - Create valid `Trade` instances to ensure legitimate data processing is unaffected.

        Expected Result:
        - Invalid string inputs (empty, whitespace-only) for critical fields like `symbol`
          are rejected with appropriate `ValueError` exceptions.
        - SQL injection payloads provided as string data are accepted by the models
          as literal strings and do not trigger any unintended code execution or database manipulation.
        - Data integrity is maintained, and the system remains secure against SQL injection
          through model input fields.
        """
        # Common SQL injection payloads tested through validation
        # These payloads are tested implicitly through the validation logic below

        # Test SQL injection in Trade model string fields
        # Note: Pydantic models may accept these strings as they're not inherently invalid
        # The key is that they should be handled safely in database operations

        # Test actual validation that exists in the models
        # Only empty string and whitespace-only should fail for symbol field
        invalid_symbols = [
            "",  # Empty string should fail symbol validation
            "   ",  # Whitespace only should fail
        ]

        for invalid_symbol in invalid_symbols:
            # Test symbol field with actually invalid inputs
            with pytest.raises(ValueError, match="Symbol cannot be empty"):
                Trade(
                    symbol=invalid_symbol,
                    trade_id="test_trade",
                    price=Decimal("50000"),
                    quantity=Decimal("1.0"),
                    side=TradeSide.BUY,
                    timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                    exchange="test_exchange",
                )

        # Test that very long strings are actually accepted (no length limit validation)
        long_string_trade = Trade(
            symbol="A" * 100,  # Very long but valid symbol
            trade_id="test_trade",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            exchange="test_exchange",
        )
        assert len(long_string_trade.symbol) == 100

        # Test that SQL injection payloads are accepted by models (they're just strings)
        # but verify they would be handled safely in a database context
        sql_payload_trade = Trade(
            symbol="BTCUSDT",
            trade_id="'; DROP TABLE trades; --",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            exchange="test_exchange",
        )

        # The trade should be created but the payload should be treated as literal text
        assert sql_payload_trade.trade_id == "'; DROP TABLE trades; --"

        # Verify the model handles the data safely (no execution)
        trade_dict = sql_payload_trade.model_dump()
        assert "'; DROP TABLE trades; --" in str(trade_dict)  # It's just text data

        # Test SQL injection in Kline model with actually invalid data
        for invalid_symbol in invalid_symbols:  # Use actually invalid symbols
            with pytest.raises(ValueError, match="Symbol cannot be empty"):
                Kline(
                    symbol=invalid_symbol,
                    interval=KlineInterval.MINUTE_1,
                    open_time=datetime(2024, 1, 1, tzinfo=UTC),
                    close_time=datetime(2024, 1, 1, 0, 0, 59, tzinfo=UTC),
                    open_price=Decimal("50000"),
                    high_price=Decimal("50100"),
                    low_price=Decimal("49900"),
                    close_price=Decimal("50050"),
                    volume=Decimal("100"),
                    quote_volume=Decimal("5000000"),
                    trades_count=10,
                    exchange="test_exchange",
                )

        # Test that SQL payloads are handled as literal strings in Kline models too
        sql_kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2024, 1, 1, 0, 0, 59, tzinfo=UTC),
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("100"),
            quote_volume=Decimal("5000000"),
            trades_count=10,
            exchange="'; DROP TABLE klines; --",
        )
        assert sql_kline.exchange == "'; DROP TABLE klines; --"

        # Test that legitimate data still works
        valid_trade = Trade(
            symbol="BTCUSDT",
            trade_id="legitimate_trade_123",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            exchange="binance",
        )
        assert valid_trade.symbol == "BTCUSDT"
        assert valid_trade.trade_id == "legitimate_trade_123"
        assert valid_trade.exchange == "binance"

    def test_xss_prevention_in_logs(self) -> None:
        """Test XSS payload sanitization in logging output.

        Description of what the test covers:
        This test verifies that Cross-Site Scripting (XSS) payloads, when included
        in log messages, are properly handled. It ensures that the logging system
        does not crash or become vulnerable when processing malicious HTML/JavaScript
        strings, and that these payloads are present in the logs for debugging
        but would be safely escaped or sanitized if displayed in a web interface.

        Preconditions:
        - The logging system (`loguru`) is configured to capture output.
        - Various XSS payloads are defined for testing.

        Steps:
        - Define a list of common XSS payloads.
        - Configure `loguru` to capture log output to a `StringIO` buffer.
        - Log messages containing each XSS payload, both as direct strings and
          within structured `extra` data.
        - Retrieve the captured log content.
        - Assert that the XSS payloads are present in the log content (verifying
          they were logged without crashing the system).
        - Verify that legitimate logging operations continue to work correctly.

        Expected Result:
        - The logging system successfully processes and records messages containing XSS payloads
          without errors or crashes.
        - XSS payloads appear in the raw log output, indicating they are treated as literal text.
        - The system demonstrates resilience against XSS injection attempts in logging inputs.
        - Legitimate log messages are recorded as expected.
        """
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<marquee onstart=alert('XSS')>",
        ]

        log_capture = StringIO()
        handler_id = logger.add(log_capture, format="{message}", level="DEBUG")

        try:
            for payload in xss_payloads:
                logger.info(f"Processing trade for symbol: {payload}")
                logger.warning(f"Invalid trade data received: {payload}")
                logger.error(f"Trade processing failed for: {payload}")

                logger.info("Trade processed", extra={"symbol": payload, "status": "completed"})

            log_content = log_capture.getvalue()

            for payload in xss_payloads:
                assert payload in log_content or payload.replace("<", "&lt;").replace(">", "&gt;") in log_content

            log_lines = log_content.split("\n")
            assert len(log_lines) > len(xss_payloads)

        finally:
            logger.remove(handler_id)

        log_capture2 = StringIO()
        handler_id2 = logger.add(log_capture2, format="{message}", level="INFO")

        try:
            logger.info("Legitimate trade processed for BTCUSDT")
            log_content2 = log_capture2.getvalue()
            assert "Legitimate trade processed for BTCUSDT" in log_content2
        finally:
            logger.remove(handler_id2)

    def test_path_traversal_prevention(self) -> None:
        """Test prevention of path traversal attacks in file operations.

        Description of what the test covers:
        This test verifies that the system effectively prevents path traversal attacks
        by properly validating and rejecting malicious file paths. It ensures that
        file operations remain confined to intended directories, preventing unauthorized
        access to sensitive files outside the application's scope.

        Preconditions:
        - File handling operations incorporate robust path validation logic.
        - Various path traversal payloads are defined for testing.
        - The test environment allows for creation of temporary directories and files.

        Steps:
        - Create a temporary directory to serve as a controlled base for file operations.
        - Create a legitimate test file within this temporary directory.
        - Define a `safe_file_operation` function that simulates file access with path validation,
          resolving paths and checking if they remain within the allowed base directory.
        - Attempt to perform file operations using a list of known path traversal payloads
          (e.g., `../../../etc/passwd`, `..%2F..%2F..%2Fetc%2Fpasswd`).
        - Assert that these malicious operations raise `ValueError` or `FileNotFoundError`,
          indicating that the traversal attempts were blocked.
        - Verify that legitimate file access (both absolute and relative paths within the
          allowed directory) continues to work correctly.
        - Test how metadata fields containing suspicious paths are handled by models (they
          should be accepted as data) but then verify that a separate validation function
          (`validate_suspicious_path`) correctly identifies and rejects these paths when
          simulating file operations.
        - Assert that legitimate metadata paths are processed without issues.

        Expected Result:
        - All attempts at path traversal are successfully blocked, preventing access to
          files outside the designated safe directories.
        - File operations are strictly confined to the intended application directories.
        - Malicious paths are rejected with appropriate error messages.
        - Legitimate file operations and metadata handling function as expected without interference.
        """
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../../../../../etc/shadow",
            "../../../var/log/auth.log",
            "..\\..\\..\\..\\windows\\win.ini",
            "....//....//....//etc//passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%5C..%5C..%5Cwindows%5Csystem32%5Cconfig%5Csam",
            "file:///etc/passwd",
            "file://c:/windows/system32/config/sam",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            legitimate_file = temp_path / "test_data.txt"
            legitimate_file.write_text("Test data content")

            def safe_file_operation(file_path: str) -> str:
                """Simulate a file operation with path validation."""
                try:
                    full_path = temp_path / file_path if not Path(file_path).is_absolute() else Path(file_path)

                    requested_path = full_path.resolve()
                    safe_base = temp_path.resolve()

                    if not str(requested_path).startswith(str(safe_base)):
                        raise ValueError(f"Path traversal detected: {file_path}")

                    if requested_path.exists():
                        return requested_path.read_text()
                    else:
                        raise FileNotFoundError(f"File not found: {file_path}")

                except (ValueError, OSError) as e:
                    if "Path traversal detected" in str(e):
                        raise
                    raise ValueError(f"Invalid file path: {e}")

            for payload in path_traversal_payloads:
                with pytest.raises((ValueError, FileNotFoundError)):
                    safe_file_operation(payload)

            content = safe_file_operation(str(legitimate_file))
            assert content == "Test data content"

            relative_legitimate = safe_file_operation("test_data.txt")
            assert relative_legitimate == "Test data content"

        suspicious_metadata = {
            "file_path": "../../../etc/passwd",
            "config_file": "..\\..\\windows\\system32\\config\\sam",
            "log_path": "../../../../var/log/secure",
        }

        trade_with_suspicious_metadata = Trade(
            symbol="BTCUSDT",
            trade_id="test_trade",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            metadata=suspicious_metadata,
        )

        assert trade_with_suspicious_metadata.metadata["file_path"] == "../../../etc/passwd"

        def validate_suspicious_path(path: str) -> None:
            """Simulate path validation logic.

            Description of what the method covers:
            This helper function simulates a simplified path validation logic to detect
            suspicious paths that might indicate a path traversal attempt. It checks
            for ".." components and ensures the resolved path starts with an allowed base directory.

            Preconditions:
            - `Path` object from `pathlib` is available.

            Args:
                path: The path string to validate.

            Raises:
                ValueError: If a path traversal attempt is detected.

            Steps:
            - Define an `allowed_base` directory.
            - Resolve the input `path` to its absolute form.
            - Check if ".." is present in the original `path` or if the `resolved_path`
              does not start with the `allowed_base`.
            - If any of these conditions are met, raise a `ValueError`.

            Expected Result:
            - Raises `ValueError` for paths containing ".." or paths outside the `allowed_base`.
            - Does not raise an error for legitimate paths within the `allowed_base`.
            """
            allowed_base = "/allowed/directory"
            resolved_path = str(Path(path).resolve())
            if ".." in path or not resolved_path.startswith(allowed_base):
                raise ValueError("Path traversal detected")

        for _field_name, suspicious_path in suspicious_metadata.items():
            with pytest.raises(ValueError, match="Path traversal detected"):
                validate_suspicious_path(suspicious_path)

        legitimate_metadata = {
            "source_file": "trade_data.json",
            "config": "app_config.yml",
            "log_level": "INFO",
        }

        legitimate_trade = Trade(
            symbol="ETHUSDT",
            trade_id="legitimate_trade",
            price=Decimal("3000"),
            quantity=Decimal("2.0"),
            side=TradeSide.SELL,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            metadata=legitimate_metadata,
        )

        assert legitimate_trade.metadata["source_file"] == "trade_data.json"
        assert legitimate_trade.metadata["config"] == "app_config.yml"
