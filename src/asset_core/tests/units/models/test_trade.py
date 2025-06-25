"""Unit tests for Trade model."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from src.asset_core.asset_core.models.trade import Trade, TradeSide


@pytest.mark.unit
class TestTradeSide:
    """Test cases for TradeSide enum."""

    def test_trade_side_values(self) -> None:
        """Test TradeSide enum string values."""
        assert TradeSide.BUY.value == "buy"
        assert TradeSide.SELL.value == "sell"

    def test_trade_side_string_conversion(self) -> None:
        """Test TradeSide enum value property access."""
        assert TradeSide.BUY.value == "buy"
        assert TradeSide.SELL.value == "sell"


@pytest.mark.unit
class TestTradeConstruction:
    """Test cases for Trade model construction."""

    def test_valid_trade_creation(self, sample_trade: Trade) -> None:
        """Test valid Trade instance creation using fixture."""
        assert sample_trade.symbol == "BTCUSDT"
        assert sample_trade.trade_id == "test_trade_123"
        assert sample_trade.price == Decimal("50000.50")
        assert sample_trade.quantity == Decimal("0.001")
        assert sample_trade.side == TradeSide.BUY
        assert isinstance(sample_trade.timestamp, datetime)
        assert sample_trade.timestamp.tzinfo == UTC

    def test_trade_creation_with_all_fields(self) -> None:
        """Test Trade creation with all optional fields provided."""
        now = datetime.now(UTC)
        received_time = now + timedelta(seconds=1)

        trade = Trade(
            symbol="ETHUSDT",
            trade_id="trade_456",
            price=Decimal("3000.25"),
            quantity=Decimal("0.5"),
            side=TradeSide.SELL,
            timestamp=now,
            exchange="binance",
            maker_order_id="maker_123",
            taker_order_id="taker_456",
            is_buyer_maker=True,
            received_at=received_time,
            metadata={"source": "websocket", "latency": 50},
        )

        assert trade.exchange == "binance"
        assert trade.maker_order_id == "maker_123"
        assert trade.taker_order_id == "taker_456"
        assert trade.is_buyer_maker is True
        assert trade.received_at == received_time
        assert trade.metadata == {"source": "websocket", "latency": 50}

    def test_trade_creation_minimal_fields(self) -> None:
        """Test Trade creation with only required fields."""
        now = datetime.now(UTC)

        trade = Trade(
            symbol="ADAUSDT",
            trade_id="minimal_trade",
            price=Decimal("1.25"),
            quantity=Decimal("100"),
            side=TradeSide.BUY,
            timestamp=now,
        )

        assert trade.symbol == "ADAUSDT"
        assert trade.exchange is None
        assert trade.maker_order_id is None
        assert trade.taker_order_id is None
        assert trade.is_buyer_maker is None
        assert trade.received_at is None
        assert trade.metadata == {}


@pytest.mark.unit
class TestTradeValidation:
    """Test cases for Trade model validation."""

    def test_symbol_validation(self) -> None:
        """Test symbol field validation and uppercase normalization."""
        trade = Trade(
            symbol="  btcusdt  ",
            trade_id="test",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )
        assert trade.symbol == "BTCUSDT"

    def test_empty_symbol_validation(self) -> None:
        """Test validation error for empty symbol string."""
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            Trade(
                symbol="",
                trade_id="test",
                price=Decimal("50000"),
                quantity=Decimal("0.001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_whitespace_symbol_validation(self) -> None:
        """Test validation error for whitespace-only symbol."""
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            Trade(
                symbol="   ",
                trade_id="test",
                price=Decimal("50000"),
                quantity=Decimal("0.001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_price_validation_positive(self) -> None:
        """Test validation that price must be positive."""
        with pytest.raises(ValidationError, match="greater than 0"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("0"),
                quantity=Decimal("0.001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_quantity_validation_positive(self) -> None:
        """Test validation that quantity must be positive."""
        with pytest.raises(ValidationError, match="greater than 0"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("50000"),
                quantity=Decimal("-0.001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_price_range_validation_minimum(self) -> None:
        """Test price minimum range validation."""
        with pytest.raises(ValidationError, match="below minimum allowed price"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("0.0000000000001"),
                quantity=Decimal("1"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_price_range_validation_maximum(self) -> None:
        """Test price maximum range validation."""
        with pytest.raises(ValidationError, match="exceeds maximum allowed price"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("20000000"),
                quantity=Decimal("0.001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_quantity_range_validation_minimum(self) -> None:
        """Test quantity minimum range validation."""
        with pytest.raises(ValidationError, match="below minimum allowed quantity"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("1"),
                quantity=Decimal("0.0000000000001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_quantity_range_validation_maximum(self) -> None:
        """Test quantity maximum range validation."""
        with pytest.raises(ValidationError, match="exceeds maximum allowed volume"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("50000"),
                quantity=Decimal("2000000000"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_volume_validation_minimum(self) -> None:
        """Test trade volume minimum validation."""
        with pytest.raises(ValidationError, match="below minimum allowed volume"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("0.00000001"),
                quantity=Decimal("0.00000001"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

    def test_volume_validation_maximum(self) -> None:
        """Test trade volume maximum validation."""
        with pytest.raises(ValidationError, match="exceeds maximum allowed volume"):
            Trade(
                symbol="BTCUSDT",
                trade_id="test",
                price=Decimal("10000000"),
                quantity=Decimal("100"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )


@pytest.mark.unit
class TestTradeTimezoneHandling:
    """Test cases for Trade model timezone handling."""

    def test_timezone_aware_timestamp(self) -> None:
        """Test timezone-aware timestamp handling."""
        utc_time = datetime.now(UTC)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="test",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=utc_time,
        )
        assert trade.timestamp.tzinfo == UTC

    def test_timezone_naive_timestamp_conversion(self) -> None:
        """Test timezone-naive timestamp is converted to UTC."""
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="test",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=naive_time,
        )
        assert trade.timestamp.tzinfo == UTC
        assert trade.timestamp.replace(tzinfo=None) == naive_time

    def test_timezone_conversion_to_utc(self) -> None:
        """Test timestamp from different timezone is converted to UTC."""
        est = timezone(timedelta(hours=-5))
        est_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)

        trade = Trade(
            symbol="BTCUSDT",
            trade_id="test",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=est_time,
        )

        assert trade.timestamp.tzinfo == UTC
        expected_utc = datetime(2023, 1, 1, 17, 0, 0, tzinfo=UTC)
        assert trade.timestamp == expected_utc

    def test_received_at_timezone_handling(self) -> None:
        """Test received_at timezone handling."""
        naive_time = datetime(2023, 1, 1, 10, 0, 0)
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="test",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            received_at=naive_time,
        )
        if trade.received_at:
            assert trade.received_at.tzinfo == UTC


@pytest.mark.unit
class TestTradeCalculatedProperties:
    """Test cases for Trade model calculated properties."""

    def test_volume_calculation(self, sample_trade: Trade) -> None:
        """Test volume calculation property."""
        expected_volume = sample_trade.price * sample_trade.quantity
        assert sample_trade.volume == expected_volume
        assert sample_trade.volume == Decimal("50.00050")

    def test_volume_calculation_precision(self) -> None:
        """Test volume calculation maintains precision."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="precision_test",
            price=Decimal("100000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        expected_volume = Decimal("100000") * Decimal("0.001")
        assert trade.volume == expected_volume


@pytest.mark.unit
class TestTradeSerialization:
    """Test cases for Trade model serialization."""

    def test_to_dict_conversion(self, sample_trade: Trade) -> None:
        """Test to_dict method."""
        trade_dict = sample_trade.to_dict()

        assert isinstance(trade_dict, dict)
        assert trade_dict["symbol"] == "BTCUSDT"
        assert trade_dict["trade_id"] == "test_trade_123"
        assert trade_dict["price"] == "50000.5"
        assert trade_dict["quantity"] == "0.001"
        assert trade_dict["volume"] == "50.0005"
        assert trade_dict["side"] == "buy"
        assert isinstance(trade_dict["timestamp"], str)
        assert trade_dict["timestamp"].endswith("Z") or "+" in trade_dict["timestamp"]

    def test_to_dict_with_optional_fields(self) -> None:
        """Test to_dict with optional fields."""
        now = datetime.now(UTC)
        received_time = now + timedelta(seconds=1)

        trade = Trade(
            symbol="ETHUSDT",
            trade_id="test_optional",
            price=Decimal("3000.25"),
            quantity=Decimal("0.5"),
            side=TradeSide.SELL,
            timestamp=now,
            exchange="binance",
            received_at=received_time,
            metadata={"test": "data"},
        )

        trade_dict = trade.to_dict()
        assert trade_dict["exchange"] == "binance"
        assert isinstance(trade_dict["received_at"], str)
        assert trade_dict["metadata"] == {"test": "data"}

    def test_to_dict_without_received_at(self, sample_trade: Trade) -> None:
        """Test to_dict when received_at is None."""
        assert sample_trade.received_at is None
        trade_dict = sample_trade.to_dict()
        assert trade_dict["received_at"] is None

    def test_model_dump_json_serializable(self, sample_trade: Trade) -> None:
        """Test model can be dumped to JSON-serializable format."""
        data = sample_trade.model_dump()

        import json

        json_str = json.dumps(data, default=str)
        assert isinstance(json_str, str)


@pytest.mark.unit
class TestTradeStringRepresentation:
    """Test cases for Trade model string representation."""

    def test_string_representation(self, sample_trade: Trade) -> None:
        """Test string representation."""
        str_repr = str(sample_trade)

        assert "BTCUSDT" in str_repr
        assert "buy" in str_repr
        assert "0.001" in str_repr
        assert "50000.50" in str_repr

    def test_string_representation_sell_side(self) -> None:
        """Test string representation for sell side."""
        trade = Trade(
            symbol="ETHUSDT",
            trade_id="sell_test",
            price=Decimal("3000"),
            quantity=Decimal("1.5"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        str_repr = str(trade)
        assert "sell" in str_repr
        assert "ETHUSDT" in str_repr


@pytest.mark.unit
class TestTradeBoundaryValues:
    """Test cases for Trade model boundary values."""

    def test_minimum_valid_values(self) -> None:
        """Test trade with minimum valid values."""
        min_price = Decimal("0.00000001")
        min_quantity = Decimal("1000000")

        trade = Trade(
            symbol="TESTUSDT",
            trade_id="min_test",
            price=min_price,
            quantity=min_quantity,
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        assert trade.price == min_price
        assert trade.quantity == min_quantity
        assert trade.volume >= Decimal("0.01")

    def test_maximum_valid_values(self) -> None:
        """Test trade with maximum valid values."""
        max_price = Decimal("1000000")
        max_quantity = Decimal("50")

        trade = Trade(
            symbol="TESTUSDT",
            trade_id="max_test",
            price=max_price,
            quantity=max_quantity,
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        assert trade.price == max_price
        assert trade.quantity == max_quantity
        assert trade.volume <= Decimal("100000000")

    def test_edge_case_timestamps(self) -> None:
        """Test edge case timestamps."""
        old_timestamp = datetime(1970, 1, 1, tzinfo=UTC)
        trade_old = Trade(
            symbol="TESTUSDT",
            trade_id="old_test",
            price=Decimal("100"),
            quantity=Decimal("1"),
            side=TradeSide.BUY,
            timestamp=old_timestamp,
        )
        assert trade_old.timestamp == old_timestamp

        future_timestamp = datetime(2050, 12, 31, tzinfo=UTC)
        trade_future = Trade(
            symbol="TESTUSDT",
            trade_id="future_test",
            price=Decimal("100"),
            quantity=Decimal("1"),
            side=TradeSide.BUY,
            timestamp=future_timestamp,
        )
        assert trade_future.timestamp == future_timestamp


@pytest.mark.unit
class TestTradeInvalidData:
    """Test cases for Trade model with invalid data."""

    def test_invalid_data_types(self, invalid_data_samples: dict[str, Any]) -> None:
        """Test various invalid data types."""
        base_data: dict[str, Any] = {
            "symbol": "BTCUSDT",
            "trade_id": "test",
            "price": Decimal("50000"),
            "quantity": Decimal("0.001"),
            "side": TradeSide.BUY,
            "timestamp": datetime.now(UTC),
        }

        for invalid_price in invalid_data_samples["invalid_price"]:
            test_data = base_data.copy()
            test_data["price"] = invalid_price
            with pytest.raises(ValidationError):
                Trade(**test_data)

        for invalid_quantity in invalid_data_samples["invalid_quantity"]:
            test_data = base_data.copy()
            test_data["quantity"] = invalid_quantity
            with pytest.raises(ValidationError):
                Trade(**test_data)

        for invalid_symbol in invalid_data_samples["invalid_symbol"]:
            test_data = base_data.copy()
            test_data["symbol"] = invalid_symbol
            with pytest.raises(ValidationError):
                Trade(**test_data)

    def test_missing_required_fields(self) -> None:
        """Test missing required fields."""
        required_fields = ["symbol", "trade_id", "price", "quantity", "side", "timestamp"]

        for field_to_remove in required_fields:
            data: dict[str, Any] = {
                "symbol": "BTCUSDT",
                "trade_id": "test",
                "price": Decimal("50000"),
                "quantity": Decimal("0.001"),
                "side": TradeSide.BUY,
                "timestamp": datetime.now(UTC),
            }
            del data[field_to_remove]

            with pytest.raises(ValidationError):
                Trade(**data)


@pytest.mark.unit
@pytest.mark.models
class TestTradeIntegration:
    """Integration test cases for Trade model."""

    def test_trade_lifecycle(self) -> None:
        """Test complete trade lifecycle."""
        trade = Trade(
            symbol="BTCUSDT",
            trade_id="lifecycle_test",
            price=Decimal("45000.75"),
            quantity=Decimal("0.002"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            metadata={"test": "lifecycle"},
        )

        assert trade.volume == Decimal("90.00150")

        trade_dict = trade.to_dict()
        assert trade_dict["volume"] == "90.0015"

        str_repr = str(trade)
        assert "lifecycle_test" not in str_repr
        assert "0.002@45000.75" in str_repr

    def test_trade_equality_and_hashing(self) -> None:
        """Test trade equality and hashing behavior."""
        now = datetime.now(UTC)

        trade1 = Trade(
            symbol="BTCUSDT",
            trade_id="same_trade",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=now,
        )

        trade2 = Trade(
            symbol="BTCUSDT",
            trade_id="same_trade",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=now,
        )

        assert trade1 == trade2

        trade3 = Trade(
            symbol="BTCUSDT",
            trade_id="different_trade",
            price=Decimal("50000"),
            quantity=Decimal("0.001"),
            side=TradeSide.BUY,
            timestamp=now,
        )

        assert trade1 != trade3
