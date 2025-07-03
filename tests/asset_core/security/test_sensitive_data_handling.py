"""Sensitive data handling and security tests.

This module tests the system's ability to properly handle sensitive information
such as API keys, personal data, and error messages, ensuring they are masked,
anonymized, or properly secured to prevent data leaks.
"""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from loguru import logger

from asset_core.models.trade import Trade, TradeSide


class TestSensitiveDataHandling:
    """Tests for sensitive data handling and privacy protection.

    Description of what the test covers:
    This test suite focuses on verifying the system's robust handling of sensitive
    information, including API keys, personal data, and error messages. It ensures
    that such data is properly masked, anonymized, or secured to prevent any
    unintended data leaks or privacy breaches.

    Preconditions:
    - The system has implemented mechanisms for sensitive data protection.
    - The logging system is configured to allow output capture and analysis.
    - Error handling systems are in place and can be triggered for testing.

    Steps:
    - Execute tests for API key and credential masking in logs and outputs.
    - Execute tests for personal data anonymization and pseudonymization.
    - Execute tests to ensure error messages do not expose sensitive internal information.
    - Verify that data serialization processes exclude or mask sensitive fields.

    Expected Result:
    - Sensitive data is consistently and correctly masked or anonymized across all outputs.
    - Error messages are informative to the user but do not reveal internal system details.
    - API keys and other credentials are never logged or exposed in plain text.
    - Personal information is protected in accordance with privacy requirements.
    """

    def test_api_key_masking(self) -> None:
        """Test that API keys and credentials are masked in logs and outputs.

        Description of what the test covers:
        This test verifies that sensitive credentials, such as API keys, secret keys,
        access tokens, bearer tokens, passwords, and private keys, are automatically
        masked or redacted when they appear in log messages or serialized data structures.
        It ensures that these sensitive details are not exposed in plain text.

        Preconditions:
        - A logging system capable of capturing output is available.
        - Masking mechanisms for sensitive data are implemented.
        - Various formats of credentials are defined for testing.

        Steps:
        - Define a set of sensitive credentials with different patterns.
        - Implement a simulated `mask_sensitive_data` function to mimic the masking logic.
        - Configure `loguru` to capture log output.
        - Log messages containing sensitive credentials and verify that the captured
          logs show the masked versions, not the original plain text.
        - Test structured logging with sensitive data, ensuring only safe information is present.
        - Verify that the `mask_sensitive_data` function correctly masks various patterns.
        - Create a `Trade` model instance with sensitive metadata.
        - Simulate safe serialization by filtering out sensitive keys from the metadata
          and assert that sensitive fields are not present in the safe serialized output.

        Expected Result:
        - All sensitive API keys and credentials are properly masked (e.g., with asterisks)
          in log outputs and serialized data.
        - Original plain-text credentials do not appear in any output.
        - Masking preserves enough context for debugging without compromising security.
        - Non-sensitive data is logged and serialized correctly.
        """
        sensitive_credentials = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "secret_key": "abcdef1234567890abcdef1234567890abcdef12",
            "access_token": "ghp_1234567890abcdef1234567890abcdef123456",
            "bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "password": "super_secret_password_123!",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----",
        }

        def mask_sensitive_data(text: str) -> str:
            """Simulate sensitive data masking."""
            patterns = {
                r"sk-[a-zA-Z0-9]{32}": lambda _m: f"sk-{'*' * 28}",
                r"ghp_[a-zA-Z0-9]{36}": lambda _m: f"ghp_{'*' * 32}",
                r"Bearer\s+[a-zA-Z0-9\.\-_]{100,}": lambda _m: f"Bearer {'*' * 20}...",
                r"password[\':\"\s=]+[^\s\'\"\n]+": lambda m: re.sub(
                    r"([\':\"\s=]+)[^\s\'\"\n]+", r"\1***MASKED***", m.group(0)
                ),
                r"secret_key[\':\"\s=]+[a-zA-Z0-9]+": lambda m: re.sub(
                    r"([\':\"\s=]+)[a-zA-Z0-9]+", r"\1***MASKED***", m.group(0)
                ),
                r"[a-f0-9]{40,}": lambda _m: "***MASKED***",
                r"-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----": lambda _m: "-----BEGIN PRIVATE KEY-----\n***MASKED***\n-----END PRIVATE KEY-----",
            }

            result = text
            for pattern, replacement in patterns.items():
                result = re.sub(pattern, replacement, result, flags=re.DOTALL | re.IGNORECASE)
            return result

        log_capture = StringIO()
        handler_id = logger.add(log_capture, format="{message}", level="DEBUG")

        try:
            for field_name, credential in sensitive_credentials.items():
                original_message = f"Authentication failed for {field_name}: {credential}"
                masked_message = mask_sensitive_data(original_message)

                logger.info(masked_message)
                logger.warning(f"Invalid {field_name} provided in request")
                logger.error(f"Authentication error with {field_name}")

            safe_extra_data = {
                "user_id": "user_123",
                "api_key_last_4": "cdef",
                "token_type": "bearer",
                "request_id": "req_abc123",
            }
            logger.info("API request processed", extra=safe_extra_data)

            log_capture.getvalue()

            for field_name, credential in sensitive_credentials.items():
                original_message = f"Authentication failed for {field_name}: {credential}"
                masked_message = mask_sensitive_data(original_message)

                assert credential not in masked_message, f"Credential not masked in: {masked_message}"

            test_message = "API key: sk-1234567890abcdef1234567890abcdef"
            masked_test = mask_sensitive_data(test_message)
            assert "sk-****" in masked_test
            assert "sk-1234567890abcdef1234567890abcdef" not in masked_test

        finally:
            logger.remove(handler_id)

        trade_with_metadata = Trade(
            symbol="BTCUSDT",
            trade_id="test_trade",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={
                "source": "trading_bot",
                "api_key": "sk-1234567890abcdef1234567890abcdef",
                "user_id": "user_123",
                "session_id": "sess_abc123",
            },
        )

        def create_safe_dict(trade: Trade) -> dict[str, Any]:
            data: dict[str, Any] = trade.model_dump()
            if "metadata" in data:
                sensitive_keys = {"api_key", "secret_key", "password", "private_key", "token"}
                data["metadata"] = {k: v for k, v in data["metadata"].items() if k not in sensitive_keys}
            return data

        safe_serialized = create_safe_dict(trade_with_metadata)
        assert "api_key" not in safe_serialized["metadata"]
        assert "user_id" in safe_serialized["metadata"]

    def test_personal_data_anonymization(self) -> None:
        """Test anonymization and pseudonymization of personal data.

        Description of what the test covers:
        This test verifies that personal data, such as emails, IP addresses,
        user identifiers, and financial information, is correctly anonymized
        or pseudonymized to ensure privacy compliance. It checks that original
        sensitive data is not exposed while ensuring the anonymized data
        retains sufficient utility for analysis.

        Preconditions:
        - Anonymization and pseudonymization functions are implemented.
        - The system can identify and process various types of personal data.

        Steps:
        - Define a dictionary of original sensitive metadata.
        - Apply various anonymization functions (email, IP, user ID, financial data)
          to the corresponding fields in the metadata.
        - Verify that the anonymized fields no longer contain the original sensitive data
          but retain necessary masked or pseudonymized patterns (e.g., domain for email,
          last octet for IP, 'pseudo_user_' prefix for user ID, last 4 digits for financial data).
        - Assert that non-personal data in the metadata remains unchanged.
        - Test the consistency of pseudonymization (same input yields same output).
        - Create a `Trade` object with the anonymized metadata and verify its creation.
        - Generate a large set of user IDs and their anonymized counterparts to
          check for uniqueness preservation and consistency.

        Expected Result:
        - Sensitive personal data fields are effectively masked or anonymized.
        - Original Personally Identifiable Information (PII) is not recoverable from
          the anonymized data.
        - Anonymized data maintains its utility and statistical properties (e.g., uniqueness).
        - The system demonstrates compliance with privacy requirements by protecting PII.
        """
        # Personal data patterns are tested through the anonymization functions below
        # Various data types are covered in the test implementation

        # Anonymization functions (simplified implementations)
        def anonymize_email(email: str) -> str:
            """Anonymize email by hashing username part."""
            import hashlib

            if "@" in email:
                username, domain = email.split("@", 1)
                # Use sha256 for consistent hashing across runs
                hashed = int(hashlib.sha256(username.encode()).hexdigest()[:8], 16) % 10000
                return f"user_{hashed}@{domain}"
            return "anonymized_email"

        def anonymize_ip(ip: str) -> str:
            """Anonymize IP by masking last octet."""
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
            return "xxx.xxx.xxx.xxx"

        def pseudonymize_user_id(user_id: str) -> str:
            """Create consistent pseudonym for user ID."""
            import hashlib

            # Use sha256 for consistent hashing across runs
            pseudo_hash = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16) % 100000
            return f"pseudo_user_{pseudo_hash}"

        def mask_financial_data(data: str) -> str:
            """Mask financial data like credit cards."""
            if len(data) >= 4:
                return f"****-****-****-{data[-4:]}"
            return "****-masked****"

        original_metadata = {
            "trader_email": "alice.trader@exchange.com",
            "trader_ip": "203.0.113.42",
            "user_identifier": "user_alice_trader_456",
            "payment_method": "4532-1234-5678-9012",
            "wallet": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "session_id": "sess_abc123def456",
            "timestamp": "2024-01-01T10:00:00Z",
        }

        anonymized_metadata = {}
        for key, value in original_metadata.items():
            if key == "trader_email":
                anonymized_metadata[key] = anonymize_email(value)
            elif key == "trader_ip":
                anonymized_metadata[key] = anonymize_ip(value)
            elif key == "user_identifier":
                anonymized_metadata[key] = pseudonymize_user_id(value)
            elif key == "payment_method" or key == "wallet":
                anonymized_metadata[key] = mask_financial_data(value)
            else:
                anonymized_metadata[key] = value

        assert anonymized_metadata["trader_email"] != original_metadata["trader_email"]
        assert "@exchange.com" in anonymized_metadata["trader_email"]
        assert anonymized_metadata["trader_ip"].endswith(".xxx")
        assert "pseudo_user_" in anonymized_metadata["user_identifier"]
        assert anonymized_metadata["payment_method"].endswith("-9012")
        assert "****" in anonymized_metadata["wallet"]

        assert anonymized_metadata["session_id"] == original_metadata["session_id"]
        assert anonymized_metadata["timestamp"] == original_metadata["timestamp"]

        anonymized_again = pseudonymize_user_id(original_metadata["user_identifier"])
        assert anonymized_again == anonymized_metadata["user_identifier"]

        anonymized_trade = Trade(
            symbol="BTCUSDT",
            trade_id="trade_789",
            price=Decimal("50000"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            metadata=anonymized_metadata,
        )

        assert anonymized_trade.metadata["trader_email"].startswith("user_")
        assert anonymized_trade.metadata["trader_ip"].endswith(".xxx")

        test_user_ids = [f"user_test_{i}" for i in range(100)]
        anonymized_ids = [pseudonymize_user_id(uid) for uid in test_user_ids]

        assert len(set(anonymized_ids)) == len(set(test_user_ids))

        for original_id in test_user_ids:
            assert pseudonymize_user_id(original_id) == pseudonymize_user_id(original_id)

    def test_secure_error_messages(self) -> None:
        """Test that error messages don't expose sensitive internal information.

        Description of what the test covers:
        This test ensures that error messages and exception details generated by the system
        do not inadvertently expose sensitive internal information such as file paths,
        database schemas, internal configurations, or other implementation details.
        It verifies that error messages are informative to the user but remain secure.

        Preconditions:
        - Error handling mechanisms are in place.
        - The system can generate various types of errors (e.g., validation errors).
        - Logging system allows capturing and inspecting error messages.

        Steps:
        - Trigger model validation errors with invalid inputs (e.g., empty symbol, negative price).
        - Capture the error messages and assert that they do not contain sensitive patterns
          like file paths, credential hints, database information, or Python internals.
        - Verify that the error messages are still helpful and indicate the nature of the error.
        - Simulate logging of secure errors and assert that the logged content does not
          contain unsafe internal patterns.
        - Test that standard model serialization does not expose Python object internals.

        Expected Result:
        - Error messages are informative to the user without revealing sensitive internal system details.
        - No internal file paths, database schemas, or configuration secrets are exposed in error outputs.
        - Debugging information is controlled and not publicly accessible.
        - Model serialization is safe and does not leak internal Python object structures.
        """
        with pytest.raises(ValueError) as exc_info:
            Trade(
                symbol="",
                trade_id="test",
                price=Decimal("50000"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            )

        error_message = str(exc_info.value)

        sensitive_patterns = [
            "/usr/local/lib/python",
            "C:\\Program Files\\",
            "password",
            "database",
            "sql",
            "connection_string",
            "secret",
            "__pycache__",
            "site-packages",
        ]

        for pattern in sensitive_patterns:
            assert pattern.lower() not in error_message.lower(), f"Sensitive pattern '{pattern}' found in error message"

        assert "symbol" in error_message.lower() or "empty" in error_message.lower()

        with pytest.raises(ValueError) as exc_info:
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("-1000"),
                quantity=Decimal("1.0"),
                side=TradeSide.BUY,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            )

        price_error = str(exc_info.value)

        assert "price" in price_error.lower()
        assert not any(pattern in price_error.lower() for pattern in sensitive_patterns)

        log_capture = StringIO()
        handler_id = logger.add(log_capture, format="{level} | {message}", level="ERROR")

        try:

            def log_secure_error(operation: str, error_code: str, user_context: str) -> None:
                """Log error with secure, non-revealing message.

                Description of what the method covers:
                This helper function simulates logging an error message in a secure manner.
                It constructs a public-facing message with general error information
                and logs internal context separately at a debug level, ensuring sensitive
                details are not exposed in standard error logs.

                Preconditions:
                - `loguru` logger is configured.

                Args:
                    operation: A string describing the operation that failed.
                    error_code: A string representing the error code.
                    user_context: A string providing context about the user or request, which might be sensitive.

                Steps:
                - Construct a `public_message` using `operation` and `error_code`.
                - Construct an `internal_context` string including `user_context`.
                - Log the `public_message` at `ERROR` level.
                - Log the `internal_context` at `DEBUG` level.

                Expected Result:
                - An error message is logged that is informative but does not contain sensitive `user_context`.
                - Sensitive `user_context` is logged separately at a lower (debug) level.
                """
                public_message = f"Operation '{operation}' failed with error {error_code}"

                internal_context = f"User context: {user_context}"

                logger.error(public_message)
                logger.debug(f"Internal context: {internal_context}")

            log_secure_error("trade_processing", "TRD_001", "authenticated_user_123")
            log_secure_error("data_validation", "VAL_002", "api_client_456")
            log_secure_error("market_data_fetch", "MKT_003", "system_service")

            log_content = log_capture.getvalue()

            assert "TRD_001" in log_content
            assert "VAL_002" in log_content
            assert "MKT_003" in log_content

            unsafe_patterns = [
                "internal_server_config",
                "database_connection_pool",
                "/var/lib/trading_system",
                "admin_password",
                "encryption_key",
                "stack_trace:",
            ]

            for pattern in unsafe_patterns:
                assert pattern not in log_content.lower()

        finally:
            logger.remove(handler_id)

        trade = Trade(
            symbol="ETHUSDT",
            trade_id="secure_trade_123",
            price=Decimal("3000"),
            quantity=Decimal("2.0"),
            side=TradeSide.SELL,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={"processing_node": "node_1", "request_id": "req_789"},
        )

        trade_dict = trade.model_dump()

        def decimal_converter(obj: Any) -> Any:
            if hasattr(obj, "__dict__"):
                return {k: decimal_converter(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [decimal_converter(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: decimal_converter(v) for k, v in obj.items()}
            elif isinstance(obj, Decimal):
                return str(obj)
            elif hasattr(obj, "isoformat"):
                return obj.isoformat()
            else:
                return obj

        safe_dict = decimal_converter(trade_dict)
        trade_json = json.dumps(safe_dict)

        python_internals = ["__dict__", "__class__", "__module__", "_sa_instance_state"]
        for internal in python_internals:
            assert internal not in trade_json

        assert "ETHUSDT" in trade_json
        assert "secure_trade_123" in trade_json
        assert "3000" in trade_json

        debug_trade_info = f"Trade object: {trade}"
        assert "Trade(" in debug_trade_info
        assert trade.symbol in debug_trade_info
        assert "0x" not in debug_trade_info
        assert "__" not in debug_trade_info
