"""ABOUTME: Unit tests specifically for Trade model functionality
ABOUTME: Testing trade-specific validation and business logic separately from general model tests
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from asset_core.models.trade import Trade, TradeSide


@pytest.mark.unit
class TestTradeBusinessLogic:
    """Unit tests for Trade model business logic."""

    def test_volume_calculation(self) -> None:
        """Test that volume is calculated correctly."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.1"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        assert trade.volume == Decimal("5000.0")

    def test_high_precision_volume_calculation(self) -> None:
        """Test volume calculation with high precision values."""
        trade = Trade(
            symbol="DOGE",
            trade_id="12345",
            price=Decimal("0.000123456789"),
            quantity=Decimal("1000000.123456789"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Volume should maintain precision
        expected_volume = Decimal("0.000123456789") * Decimal("1000000.123456789")
        assert trade.volume == expected_volume

    def test_trade_side_validation(self) -> None:
        """Test that TradeSide is properly validated."""
        timestamp = datetime.now(UTC)

        # Valid sides should work
        for side in [TradeSide.BUY, TradeSide.SELL]:
            trade = Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side=side,
                timestamp=timestamp,
            )
            assert trade.side == side

        # Invalid side should raise ValidationError
        with pytest.raises(ValidationError):
            Trade(
                symbol="BTCUSDT",
                trade_id="12345",
                price=Decimal("1.0"),
                quantity=Decimal("1.0"),
                side="invalid_side",
                timestamp=timestamp,
            )

    def test_trade_string_representation(self) -> None:
        """Test Trade string representation includes key information."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=timestamp,
        )

        str_repr = str(trade)
        assert "BTCUSDT" in str_repr
        assert "buy" in str_repr
        assert "0.001" in str_repr
        assert "50000" in str_repr
        assert "2023-01-01T12:00:00+00:00" in str_repr

    def test_trade_serialization_precision(self) -> None:
        """Test that Trade serialization maintains decimal precision."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.123456789"),
            quantity=Decimal("0.001234567890"),
            side=TradeSide.BUY,
            timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        data = trade.to_dict()

        # Check that precision is maintained in string format
        assert data["price"] == "50000.123456789"
        assert data["quantity"] == "0.00123456789"
        # Volume should also maintain precision
        expected_volume = str((Decimal("50000.123456789") * Decimal("0.001234567890")).normalize())
        assert data["volume"] == expected_volume

    def test_optional_fields_behavior(self) -> None:
        """Test behavior of optional fields."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Optional fields should have default values
        assert trade.exchange is None
        assert trade.maker_order_id is None
        assert trade.taker_order_id is None
        assert trade.is_buyer_maker is None
        assert trade.received_at is None
        assert trade.metadata == {}

    def test_trade_with_all_optional_fields(self) -> None:
        """Test trade creation with all optional fields provided."""
        timestamp = datetime.now(UTC)
        received_at = datetime.now(UTC)
        metadata = {"source": "api", "latency_ms": 45}

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=timestamp,
            exchange="binance",
            maker_order_id="maker123",
            taker_order_id="taker456",
            is_buyer_maker=True,
            received_at=received_at,
            metadata=metadata,
        )

        assert trade.exchange == "binance"
        assert trade.maker_order_id == "maker123"
        assert trade.taker_order_id == "taker456"
        assert trade.is_buyer_maker is True
        assert trade.received_at == received_at
        assert trade.metadata == metadata

    @pytest.mark.skip(reason="待動態最小值分支處理 - 需要基於資產類型的動態最小值")
    def test_extreme_value_handling(self) -> None:
        """Test trade handling of extreme but valid values."""
        # Test very small values
        small_trade = Trade(
            symbol="MICROTOKEN",
            trade_id="small_trade",
            price=Decimal("0.000000000001"),  # Minimum allowed
            quantity=Decimal("0.000000000001"),  # Minimum allowed
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Volume should be calculated correctly even for tiny amounts
        expected_volume = Decimal("0.000000000001") * Decimal("0.000000000001")
        assert small_trade.volume == expected_volume
        assert small_trade.volume >= Decimal("0.001")  # Should pass volume validation

        # Test large values
        large_trade = Trade(
            symbol="WHALE",
            trade_id="large_trade",
            price=Decimal("1000000000"),  # Maximum allowed
            quantity=Decimal("10.0"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        expected_large_volume = Decimal("1000000000") * Decimal("10.0")
        assert large_trade.volume == expected_large_volume
        assert large_trade.volume <= Decimal("10000000000")  # Should pass volume validation

    def test_trade_id_uniqueness_assumption(self) -> None:
        """Test that trade_id is treated as unique identifier."""
        timestamp = datetime.now(UTC)

        # Same trade_id should be allowed (system doesn't enforce uniqueness)
        trade1 = Trade(
            symbol="BTCUSDT",
            trade_id="duplicate_id",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=timestamp,
        )

        trade2 = Trade(
            symbol="ETHUSDT",  # Different symbol, same ID
            trade_id="duplicate_id",
            price=Decimal("2.0"),
            quantity=Decimal("2.0"),
            side=TradeSide.SELL,
            timestamp=timestamp,
        )

        # Both should be valid - uniqueness is exchange responsibility
        assert trade1.trade_id == trade2.trade_id
        assert trade1.symbol != trade2.symbol

    def test_decimal_type_preservation(self) -> None:
        """Test that Decimal types are preserved throughout operations."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="12345",
            price=Decimal("50000.0"),
            quantity=Decimal("0.1"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # All financial fields should remain as Decimal
        assert isinstance(trade.price, Decimal)
        assert isinstance(trade.quantity, Decimal)
        assert isinstance(trade.volume, Decimal)

        # Volume calculation should return Decimal
        calculated_volume = trade.price * trade.quantity
        assert isinstance(calculated_volume, Decimal)
        assert calculated_volume == trade.volume

    def test_timestamp_handling_edge_cases(self) -> None:
        """Test edge cases in timestamp handling."""
        # Future timestamp should be allowed
        future_time = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="future_trade",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=future_time,
        )

        assert trade.timestamp == future_time

        # Very old timestamp should be allowed
        old_time = datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)
        old_trade = Trade(
            symbol="OLDCOIN",
            trade_id="old_trade",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=old_time,
        )

        assert old_trade.timestamp == old_time

    def test_metadata_flexibility(self) -> None:
        """Test that metadata field accepts various data types."""
        complex_metadata = {
            "string_field": "value",
            "numeric_field": 123,
            "boolean_field": True,
            "list_field": [1, 2, 3],
            "nested_dict": {
                "sub_field": "sub_value",
                "sub_numeric": 456.789,
            },
            "null_field": None,
        }

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="metadata_test",
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            metadata=complex_metadata,
        )

        assert trade.metadata == complex_metadata
        # Verify nested access works
        assert trade.metadata["nested_dict"]["sub_field"] == "sub_value"
