# ABOUTME: 測試asset_core.types模組與其他模組的整合功能
# ABOUTME: 驗證自定義類型在storage、models、events模組中的序列化和反序列化

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asset_core.models.events import KlineEvent, TradeEvent
from asset_core.models.kline import Kline, KlineInterval
from asset_core.models.trade import Trade, TradeSide
from asset_core.types.common import (
    ExchangeName,
    Failure,
    OrderId,
    ProviderName,
    StorageKey,
    Success,
    Symbol,
    TradeId,
)


@pytest.mark.integration
class TestTypesWithModels:
    """Integration tests for types with models module.

    Verifies that custom types integrate properly with Pydantic models
    in the models module, including validation and serialization.
    """

    def test_types_in_trade_model(self) -> None:
        """Test custom types integration with Trade model.

        Description of what the test covers:
        Verifies that custom types (Symbol, TradeId, Price, Quantity)
        work correctly when used in Trade model instantiation and serialization.

        Preconditions:
        - None.

        Steps:
        - Create Trade instance using custom types
        - Verify model accepts custom types
        - Test serialization preserves type information
        - Verify deserialization recreates proper types

        Expected Result:
        - Trade model should work seamlessly with custom types
        """
        # Create Trade using custom types
        symbol = Symbol("BTCUSDT")
        trade_id = TradeId("trade_12345")
        price = Decimal("50000.50")
        quantity = Decimal("0.001")

        trade = Trade(
            symbol=symbol,
            trade_id=trade_id,
            price=price,
            quantity=quantity,
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
        )

        # Verify types are preserved
        assert trade.symbol == symbol
        assert trade.trade_id == trade_id
        assert trade.price == price
        assert trade.quantity == quantity
        assert isinstance(trade.symbol, str)  # NewType maintains underlying type
        assert isinstance(trade.trade_id, str)
        assert isinstance(trade.price, Decimal)
        assert isinstance(trade.quantity, Decimal)

        # Test serialization
        trade_dict = trade.model_dump()
        assert isinstance(trade_dict, dict)
        assert trade_dict["symbol"] == str(symbol)
        assert trade_dict["trade_id"] == str(trade_id)

        # Test JSON serialization
        json_str = trade.model_dump_json()
        assert isinstance(json_str, str)
        parsed_data = json.loads(json_str)
        assert parsed_data["symbol"] == str(symbol)
        assert parsed_data["trade_id"] == str(trade_id)

    def test_types_in_kline_model(self) -> None:
        """Test custom types integration with Kline model.

        Description of what the test covers:
        Verifies that custom types work correctly when used in Kline model
        instantiation, validation, and serialization.

        Preconditions:
        - None.

        Steps:
        - Create Kline instance using custom types
        - Verify model validation with custom types
        - Test serialization and deserialization

        Expected Result:
        - Kline model should integrate properly with custom types
        """
        # Create Kline using custom types
        symbol = Symbol("ETHUSDT")
        open_price = Decimal("3000.00")
        high_price = Decimal("3100.00")
        low_price = Decimal("2950.00")
        close_price = Decimal("3050.00")
        volume = Decimal("1000.5")

        kline = Kline(
            symbol=symbol,
            interval=KlineInterval.MINUTE_1,
            open_time=datetime.now(UTC).replace(second=0, microsecond=0),
            close_time=datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(minutes=1),
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            quote_volume=Decimal("1500000.0"),  # Added missing field
            trades_count=100,  # Added missing field
            taker_buy_base_asset_volume=Decimal("500.0"),
            taker_buy_quote_asset_volume=Decimal("1500000.0"),
        )

        # Verify types are preserved
        assert kline.symbol == symbol
        assert kline.open_price == open_price
        assert kline.high_price == high_price
        assert kline.low_price == low_price
        assert kline.close_price == close_price
        assert kline.volume == volume

        # Test serialization preserves precision
        kline_dict = kline.model_dump()
        assert isinstance(kline_dict["volume"], Decimal)  # Decimal should remain Decimal

        # Test round-trip serialization
        json_str = kline.model_dump_json()
        parsed_data = json.loads(json_str)
        assert parsed_data["symbol"] == str(symbol)

    def test_types_in_event_models(self) -> None:
        """Test custom types integration with Event models.

        Description of what the test covers:
        Verifies that custom types work correctly in event model
        hierarchies and maintain type safety across event creation
        and processing.

        Preconditions:
        - None.

        Steps:
        - Create TradeEvent using custom types
        - Create KlineEvent using custom types
        - Verify event serialization with custom types
        - Test event type discrimination

        Expected Result:
        - Event models should properly handle custom types
        """
        # Create Trade for TradeEvent
        symbol = Symbol("DOGEUSDT")
        trade = Trade(
            symbol=symbol,
            trade_id=TradeId("trade_999"),
            price=Decimal("0.08"),
            quantity=Decimal("1000.0"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
        )

        # Create TradeEvent
        trade_event = TradeEvent(source=ProviderName("TestProvider"), timestamp=datetime.now(UTC), data=trade)

        # Verify event contains custom types
        assert trade_event.data.symbol == symbol
        assert isinstance(trade_event.source, str)  # NewType preserved as string
        assert isinstance(trade_event.data.symbol, str)

        # Create Kline for KlineEvent
        kline = Kline(
            symbol=symbol,
            interval=KlineInterval.MINUTE_5,
            open_time=datetime.now(UTC).replace(minute=(datetime.now(UTC).minute // 5) * 5, second=0, microsecond=0),
            close_time=datetime.now(UTC).replace(minute=(datetime.now(UTC).minute // 5) * 5, second=0, microsecond=0)
            + timedelta(minutes=5),  # Ensure close_time is after open_time
            open_price=Decimal("0.081"),
            high_price=Decimal("0.082"),
            low_price=Decimal("0.079"),
            close_price=Decimal("0.080"),
            volume=Decimal("50000.0"),
            quote_volume=Decimal("4000.0"),  # Added missing field
            trades_count=250,
            taker_buy_base_asset_volume=Decimal("25000.0"),
            taker_buy_quote_asset_volume=Decimal("2000.0"),
        )

        # Create KlineEvent
        kline_event = KlineEvent(source=ProviderName("TestProvider"), timestamp=datetime.now(UTC), data=kline)

        # Verify event contains custom types
        assert kline_event.data.symbol == symbol
        assert isinstance(kline_event.source, str)

        # Test event serialization
        trade_event_dict = trade_event.model_dump()
        assert trade_event_dict["data"]["symbol"] == str(symbol)

        kline_event_dict = kline_event.model_dump()
        assert kline_event_dict["data"]["symbol"] == str(symbol)


@pytest.mark.integration
class TestTypesWithStorage:
    """Integration tests for types with storage operations.

    Verifies that custom types can be properly stored, retrieved,
    and queried in storage systems while maintaining type integrity.
    """

    def test_storage_key_operations(self) -> None:
        """Test StorageKey type in storage operations.

        Description of what the test covers:
        Verifies that StorageKey type can be used for storage operations
        and maintains proper key semantics.

        Preconditions:
        - None.

        Steps:
        - Create StorageKey instances
        - Test key construction patterns
        - Verify key uniqueness and comparison

        Expected Result:
        - StorageKey should work properly for storage indexing
        """
        # Test storage key creation
        symbol = Symbol("BTCUSDT")
        timestamp = datetime.now(UTC)

        # Create storage keys for different data types
        trade_key = StorageKey(f"trade:{symbol}:{timestamp.timestamp()}")
        kline_key = StorageKey(f"kline:{symbol}:1m:{timestamp.timestamp()}")
        metadata_key = StorageKey(f"metadata:{symbol}")

        # Verify keys are strings but semantically distinct
        assert isinstance(trade_key, str)
        assert isinstance(kline_key, str)
        assert isinstance(metadata_key, str)

        # Test key uniqueness
        assert trade_key != kline_key
        assert trade_key != metadata_key
        assert kline_key != metadata_key

        # Test key patterns
        assert trade_key.startswith("trade:")
        assert kline_key.startswith("kline:")
        assert metadata_key.startswith("metadata:")

        # Test key sorting (important for range queries)
        keys = [metadata_key, trade_key, kline_key]
        sorted_keys = sorted(keys)
        assert isinstance(sorted_keys[0], str)
        assert len(sorted_keys) == 3

    def test_serialization_with_custom_types(self) -> None:
        """Test serialization/deserialization with custom types.

        Description of what the test covers:
        Verifies that data containing custom types can be serialized
        to storage formats and deserialized while preserving type information.

        Preconditions:
        - None.

        Steps:
        - Create data structures with custom types
        - Serialize to JSON format
        - Deserialize and verify type preservation
        - Test round-trip serialization

        Expected Result:
        - Custom types should serialize/deserialize correctly
        """
        # Create complex data structure with custom types
        trade_data = {
            "symbol": Symbol("ADAUSDT"),
            "exchange": ExchangeName("Binance"),
            "trade_id": TradeId("987654321"),
            "order_id": OrderId("order_456"),
            "price": Decimal("1.25"),
            "quantity": Decimal("800.0"),
            "timestamp": datetime.now(UTC),
        }

        # Custom JSON encoder for our types
        def custom_encoder(obj: Any) -> Any:
            if isinstance(obj, Decimal):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Symbol | ExchangeName | TradeId | OrderId):
                return str(obj)
            return obj

        # Serialize to JSON
        json_data = json.dumps(trade_data, default=custom_encoder)
        assert isinstance(json_data, str)

        # Deserialize from JSON
        parsed_data = json.loads(json_data)
        assert isinstance(parsed_data, dict)

        # Verify data integrity (note: types are converted to strings in JSON)
        assert parsed_data["symbol"] == str(trade_data["symbol"])
        assert parsed_data["exchange"] == str(trade_data["exchange"])
        assert parsed_data["trade_id"] == str(trade_data["trade_id"])
        assert parsed_data["order_id"] == str(trade_data["order_id"])
        assert parsed_data["price"] == str(trade_data["price"])
        assert parsed_data["quantity"] == str(trade_data["quantity"])

        # Test reconstruction of types from serialized data
        reconstructed_symbol = Symbol(parsed_data["symbol"])
        reconstructed_exchange = ExchangeName(parsed_data["exchange"])
        reconstructed_price = Decimal(parsed_data["price"])
        reconstructed_quantity = Decimal(parsed_data["quantity"])

        assert reconstructed_symbol == trade_data["symbol"]
        assert reconstructed_exchange == trade_data["exchange"]
        assert reconstructed_price == trade_data["price"]
        assert reconstructed_quantity == trade_data["quantity"]

    def test_query_filtering_with_custom_types(self) -> None:
        """Test query filtering operations with custom types.

        Description of what the test covers:
        Verifies that custom types can be used in query filtering
        operations, comparisons, and range queries.

        Preconditions:
        - None.

        Steps:
        - Create collections of data with custom types
        - Perform filtering operations using custom types
        - Test comparison operations
        - Verify query result correctness

        Expected Result:
        - Custom types should support query operations properly
        """
        # Create sample data with custom types
        symbols = [Symbol("BTCUSDT"), Symbol("ETHUSDT"), Symbol("ADAUSDT")]
        prices = [Decimal("50000"), Decimal("3000"), Decimal("1.25")]
        exchanges = [ExchangeName("Binance"), ExchangeName("Coinbase"), ExchangeName("Kraken")]

        # Create trade records
        trade_records: list[dict[str, Any]] = []
        for i, (symbol, price, exchange) in enumerate(zip(symbols, prices, exchanges, strict=False)):
            trade_records.append(
                {"id": i, "symbol": symbol, "price": price, "exchange": exchange, "timestamp": datetime.now(UTC)}
            )

        # Test filtering by symbol
        btc_trades = [record for record in trade_records if record["symbol"] == Symbol("BTCUSDT")]
        assert len(btc_trades) == 1
        assert btc_trades[0]["symbol"] == Symbol("BTCUSDT")

        # Test filtering by exchange
        binance_trades = [record for record in trade_records if record["exchange"] == ExchangeName("Binance")]
        assert len(binance_trades) == 1
        assert binance_trades[0]["exchange"] == ExchangeName("Binance")

        # Test price range filtering
        high_price_trades = [record for record in trade_records if record["price"] > Decimal("1000")]
        assert len(high_price_trades) == 2  # BTC and ETH

        low_price_trades = [record for record in trade_records if record["price"] < Decimal("10")]
        assert len(low_price_trades) == 1  # ADA

        # Test symbol sorting
        sorted_by_symbol = sorted(trade_records, key=lambda x: str(x["symbol"]))
        expected_order = ["ADAUSDT", "BTCUSDT", "ETHUSDT"]  # Alphabetical order
        actual_order = [str(record["symbol"]) for record in sorted_by_symbol]
        assert actual_order == expected_order


@pytest.mark.integration
class TestResultTypesIntegration:
    """Integration tests for Result types in error handling scenarios.

    Verifies that Result types integrate properly with application
    error handling patterns and can be used across module boundaries.
    """

    def test_result_types_in_data_processing(self) -> None:
        """Test Result types in data processing pipelines.

        Description of what the test covers:
        Verifies that Result types can be used effectively in data
        processing pipelines to handle success and failure cases
        across multiple processing stages.

        Preconditions:
        - None.

        Steps:
        - Create processing pipeline using Result types
        - Test success path through pipeline
        - Test failure path and error propagation
        - Verify error handling consistency

        Expected Result:
        - Result types should enable robust error handling in pipelines
        """

        def validate_symbol(symbol_str: str) -> Success[Symbol] | Failure[Symbol]:
            """Validate and convert string to Symbol."""
            if not symbol_str or not symbol_str.strip():
                return Failure(ValueError("Symbol cannot be empty"))
            if len(symbol_str) < 3:
                return Failure(ValueError("Symbol too short"))
            return Success(Symbol(symbol_str.upper().strip()))

        def validate_price(price_str: str) -> Success[Decimal] | Failure[Decimal]:
            """Validate and convert string to Price."""
            try:
                price = Decimal(price_str)
                if price <= 0:
                    return Failure(ValueError("Price must be positive"))
                return Success(price)
            except Exception as e:
                return Failure(e)

        def create_trade_data(
            symbol_result: Success[Symbol] | Failure[Symbol], price_result: Success[Decimal] | Failure[Decimal]
        ) -> Success[dict[str, Any]] | Failure[dict[str, Any]]:
            """Combine validated data into trade record."""
            if isinstance(symbol_result, Failure):
                return Failure(symbol_result.error)
            if isinstance(price_result, Failure):
                return Failure(price_result.error)

            return Success(
                {"symbol": symbol_result.value, "price": price_result.value, "created_at": datetime.now(UTC)}
            )

        # Test successful processing pipeline
        symbol_result = validate_symbol("btcusdt")
        price_result = validate_price("50000.50")
        trade_result = create_trade_data(symbol_result, price_result)

        assert isinstance(symbol_result, Success)
        assert symbol_result.value == Symbol("BTCUSDT")
        assert isinstance(price_result, Success)
        assert price_result.value == Decimal("50000.50")
        assert isinstance(trade_result, Success)
        assert trade_result.value["symbol"] == Symbol("BTCUSDT")
        assert trade_result.value["price"] == Decimal("50000.50")

        # Test failure in symbol validation
        bad_symbol_result = validate_symbol("")
        good_price_result = validate_price("100.0")
        failed_trade_result = create_trade_data(bad_symbol_result, good_price_result)

        assert isinstance(bad_symbol_result, Failure)
        assert isinstance(failed_trade_result, Failure)
        assert "empty" in str(failed_trade_result.error)

        # Test failure in price validation
        good_symbol_result = validate_symbol("ETHUSDT")
        bad_price_result = validate_price("-100")
        failed_price_trade_result = create_trade_data(good_symbol_result, bad_price_result)

        assert isinstance(bad_price_result, Failure)
        assert isinstance(failed_price_trade_result, Failure)
        assert "positive" in str(failed_price_trade_result.error)

    def test_result_types_with_storage_operations(self) -> None:
        """Test Result types in storage operation scenarios.

        Description of what the test covers:
        Verifies that Result types can be used to handle storage
        operation outcomes, including successful saves and various
        failure conditions.

        Preconditions:
        - None.

        Steps:
        - Simulate storage operations returning Result types
        - Test successful storage scenarios
        - Test various failure scenarios
        - Verify error information preservation

        Expected Result:
        - Result types should provide clear success/failure semantics for storage
        """

        def simulate_save_trade(trade_data: dict[str, Any]) -> Success[StorageKey] | Failure[StorageKey]:
            """Simulate saving trade data to storage."""
            # Simulate validation
            if "symbol" not in trade_data:
                return Failure(ValueError("Symbol required for trade"))
            if "price" not in trade_data:
                return Failure(ValueError("Price required for trade"))

            # Simulate storage key generation
            symbol = trade_data["symbol"]
            timestamp = trade_data.get("timestamp", datetime.now(UTC))
            storage_key = StorageKey(f"trade:{symbol}:{timestamp.timestamp()}")

            return Success(storage_key)

        def simulate_load_trade(key: StorageKey) -> Success[dict[str, Any]] | Failure[dict[str, Any]]:
            """Simulate loading trade data from storage."""
            # Simulate key validation
            if not key.startswith("trade:"):
                return Failure(KeyError(f"Invalid trade key format: {key}"))

            # Simulate successful load
            parts = key.split(":")
            if len(parts) >= 2:
                symbol = parts[1]
                return Success({"symbol": Symbol(symbol), "price": Decimal("100.0"), "loaded_at": datetime.now(UTC)})

            return Failure(ValueError(f"Cannot parse key: {key}"))

        # Test successful save operation
        trade_data = {"symbol": Symbol("LINKUSDT"), "price": Decimal("25.50"), "timestamp": datetime.now(UTC)}

        save_result = simulate_save_trade(trade_data)
        assert isinstance(save_result, Success)
        assert isinstance(save_result.value, str)  # StorageKey is string-based
        assert save_result.value.startswith("trade:LINKUSDT:")

        # Test successful load operation
        load_result = simulate_load_trade(save_result.value)
        assert isinstance(load_result, Success)
        assert load_result.value["symbol"] == Symbol("LINKUSDT")
        assert isinstance(load_result.value["price"], Decimal)

        # Test save failure - missing data
        incomplete_data = {"symbol": Symbol("INCOMPLETEUSDT")}  # Missing price
        save_failure = simulate_save_trade(incomplete_data)
        assert isinstance(save_failure, Failure)
        assert "Price required" in str(save_failure.error)

        # Test load failure - invalid key
        invalid_key = StorageKey("invalid:key:format")
        load_failure = simulate_load_trade(invalid_key)
        assert isinstance(load_failure, Failure)
        assert "Invalid trade key format" in str(load_failure.error)


@pytest.mark.integration
class TestTypeInteroperability:
    """Integration tests for type interoperability across modules.

    Verifies that custom types work seamlessly when passed between
    different modules and maintain their semantic meaning.
    """

    def test_cross_module_type_usage(self) -> None:
        """Test custom types used across multiple modules.

        Description of what the test covers:
        Verifies that custom types can be created in one context,
        passed through multiple modules, and maintain their
        semantic meaning and validation properties.

        Preconditions:
        - None.

        Steps:
        - Create custom types in various contexts
        - Pass types through different processing stages
        - Verify type integrity is maintained
        - Test type validation across boundaries

        Expected Result:
        - Types should maintain consistency across module boundaries
        """
        # Simulate data flow across modules
        # 1. Data ingestion (creates raw types)
        raw_symbol = "  btcusdt  "  # Raw input with whitespace
        raw_price = "50000.123456"
        raw_exchange = "BINANCE"

        # 2. Data validation and normalization
        normalized_symbol = Symbol(raw_symbol.strip().upper())
        validated_price = Decimal(raw_price)
        normalized_exchange = ExchangeName(raw_exchange.title())

        assert normalized_symbol == Symbol("BTCUSDT")
        assert validated_price == Decimal("50000.123456")
        assert normalized_exchange == ExchangeName("Binance")

        # 3. Model creation (models module)
        trade = Trade(
            symbol=normalized_symbol,
            trade_id=TradeId("cross_module_test"),
            price=validated_price,
            quantity=Decimal("0.1"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            exchange=normalized_exchange,
        )

        # 4. Event creation (events module)
        trade_event = TradeEvent(source=ProviderName("CrossModuleTest"), timestamp=datetime.now(UTC), data=trade)

        # 5. Storage key generation (storage module)
        storage_key = StorageKey(f"trade:{trade.symbol}:{trade.timestamp.timestamp()}")

        # Verify type consistency across all stages
        assert trade.symbol == normalized_symbol
        assert trade.exchange == normalized_exchange
        assert trade_event.data.symbol == normalized_symbol
        assert storage_key.startswith(f"trade:{normalized_symbol}:")

        # Verify types maintain their underlying properties
        assert isinstance(trade.symbol, str)
        assert isinstance(trade.exchange, str)
        assert isinstance(trade.price, Decimal)
        assert isinstance(storage_key, str)

        # Test serialization maintains type information
        event_json = trade_event.model_dump_json()
        parsed_event = json.loads(event_json)

        # Reconstructed types should equal original
        reconstructed_symbol = Symbol(parsed_event["data"]["symbol"])
        reconstructed_exchange = ExchangeName(parsed_event["data"]["exchange"])

        assert reconstructed_symbol == normalized_symbol
        assert reconstructed_exchange == normalized_exchange

    def test_type_validation_propagation(self) -> None:
        """Test validation error propagation across type boundaries.

        Description of what the test covers:
        Verifies that validation errors from custom types are properly
        propagated and handled when types are used in complex nested
        structures across module boundaries.

        Preconditions:
        - None.

        Steps:
        - Create scenarios with invalid type values
        - Verify validation errors are raised appropriately
        - Test error message clarity and usefulness
        - Verify error handling consistency

        Expected Result:
        - Validation errors should be clear and properly propagated
        """
        # Test invalid symbol propagation
        with pytest.raises(ValueError):  # Should raise validation error in Trade creation
            Trade(
                symbol=Symbol(""),  # Empty symbol should be caught by Trade validation
                trade_id=TradeId("test"),
                price=Decimal("100"),
                quantity=Decimal("1"),
                side=TradeSide.BUY,
                timestamp=datetime.now(UTC),
            )

        # Test that valid custom types work in complex nested scenarios
        valid_symbol = Symbol("VALIDUSDT")
        valid_exchange = ExchangeName("ValidExchange")
        valid_trade_id = TradeId("valid_123")

        # This should work without issues
        valid_trade = Trade(
            symbol=valid_symbol,
            trade_id=valid_trade_id,
            price=Decimal("100.50"),
            quantity=Decimal("2.0"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
            exchange=valid_exchange,
        )

        valid_event = TradeEvent(source=ProviderName("ValidProvider"), timestamp=datetime.now(UTC), data=valid_trade)

        # Verify all nested types are preserved
        assert valid_event.data.symbol == valid_symbol
        assert valid_event.data.symbol == valid_symbol
        assert valid_event.data.exchange == valid_exchange
        assert isinstance(valid_event.source, str)

    def test_optional_types_integration(self) -> None:
        """Test optional custom types in integration scenarios.

        Description of what the test covers:
        Verifies that optional versions of custom types work properly
        when used in models and across module boundaries, handling
        both present and None values correctly.

        Preconditions:
        - None.

        Steps:
        - Create models with optional custom types
        - Test with None values
        - Test with present values
        - Verify serialization handles optional types

        Expected Result:
        - Optional types should work correctly in all scenarios
        """
        # Create trade with minimal required fields (optional fields as None)
        minimal_trade = Trade(
            symbol=Symbol("MINIMALUSDT"),
            trade_id=TradeId("minimal_123"),
            price=Decimal("1.0"),
            quantity=Decimal("1.0"),
            side=TradeSide.BUY,
            timestamp=datetime.now(UTC),
            # exchange is optional and defaults to None
        )

        # Verify optional fields are None
        assert minimal_trade.exchange is None
        assert minimal_trade.received_at is None

        # Create trade with optional fields present
        full_trade = Trade(
            symbol=Symbol("FULLUSDT"),
            trade_id=TradeId("full_456"),
            price=Decimal("2.0"),
            quantity=Decimal("2.0"),
            side=TradeSide.SELL,
            timestamp=datetime.now(UTC),
            exchange=ExchangeName("FullExchange"),
            received_at=datetime.now(UTC),
        )

        # Verify optional fields are present
        assert full_trade.exchange == ExchangeName("FullExchange")
        assert full_trade.received_at is not None

        # Test serialization handles optional types correctly
        minimal_dict = minimal_trade.model_dump()
        full_dict = full_trade.model_dump()

        assert minimal_dict["exchange"] is None
        assert full_dict["exchange"] == "FullExchange"

        # Test JSON serialization
        minimal_json = minimal_trade.model_dump_json()
        full_json = full_trade.model_dump_json()

        minimal_parsed = json.loads(minimal_json)
        full_parsed = json.loads(full_json)

        assert minimal_parsed["exchange"] is None
        assert full_parsed["exchange"] == "FullExchange"
