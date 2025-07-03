from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.events import (
    BaseEvent,
    ConnectionEvent,
    ConnectionStatus,
    ErrorEvent,
    EventPriority,
    EventType,
    KlineEvent,
    TradeEvent,
)
from asset_core.models.kline import Kline
from asset_core.models.trade import Trade


@pytest.mark.integration
@pytest.mark.models
class TestEventIntegration:
    """Integration test cases for Event models."""

    def test_event_lifecycle_with_trade(self, sample_trade: Trade) -> None:
        """Test complete event lifecycle with trade data."""
        event = TradeEvent(
            source="binance",
            data=sample_trade,
            symbol="BTCUSDT",
            correlation_id="trade_batch_123",
            metadata={"latency_ms": 15},
        )

        assert event.event_type == EventType.TRADE
        assert event.data.volume == Decimal("50.00050")

        event_dict = event.to_dict()
        assert event_dict["correlation_id"] == "trade_batch_123"
        assert event_dict["metadata"]["latency_ms"] == 15

        str_repr = str(event)
        assert event.event_id in str_repr

    def test_event_lifecycle_with_kline(self, sample_kline: Kline) -> None:
        """Test complete event lifecycle with kline data."""
        event = KlineEvent(source="binance", data=sample_kline, symbol="BTCUSDT", priority=EventPriority.NORMAL)

        assert event.event_type == EventType.KLINE
        assert event.data.is_bullish is True

        event_dict = event.to_dict()
        assert event_dict["priority"] == 1

        _str_repr = str(event)

    def test_event_chain_with_correlation_id(self) -> None:
        """Test event chain using correlation ID."""
        correlation_id = "chain_123"

        conn_event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED, source="websocket", correlation_id=correlation_id
        )

        error_event = ErrorEvent(error="Connection lost", source="websocket", correlation_id=correlation_id)

        assert conn_event.correlation_id == correlation_id
        assert error_event.correlation_id == correlation_id
        assert conn_event.correlation_id == error_event.correlation_id

    def test_event_equality_and_uniqueness(self) -> None:
        """Test event equality and uniqueness."""
        event1: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={"key": "value"})

        event2: BaseEvent[Any] = BaseEvent(event_type=EventType.SYSTEM, source="test", data={"key": "value"})

        assert event1 != event2
        assert event1.event_id != event2.event_id

        assert event1.data == event2.data
        assert event1.event_type == event2.event_type
        assert event1.source == event2.source
