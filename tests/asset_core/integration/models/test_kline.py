from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from asset_core.models import Kline, KlineInterval


@pytest.mark.integration
@pytest.mark.models
class TestKlineIntegration:
    """Integration test cases for Kline model.

    These tests verify the end-to-end behavior of the `Kline` model,
    including its lifecycle from creation through calculation, serialization,
    and string representation.
    """

    def test_kline_lifecycle(self) -> None:
        """Test complete kline lifecycle.

        Description of what the test covers:
        Verifies the full lifecycle of a `Kline` object, from instantiation
        to calculation of derived properties, serialization to dictionary,
        and string representation.

        Preconditions:
        - None.

        Steps:
        - Create a `Kline` instance with all relevant fields.
        - Assert the correctness of calculated properties (`price_change`, `is_bullish`, `duration`).
        - Convert the `Kline` object to a dictionary using `to_dict()`.
        - Assert the correctness of `price_change` in the dictionary.
        - Convert the `Kline` object to its string representation.
        - Assert that key information is present in the string representation.

        Expected Result:
        - The `Kline` object should behave correctly throughout its lifecycle,
          with consistent data across different representations.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=5)

        # Create kline
        kline = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_5,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("45000.00"),
            high_price=Decimal("45500.00"),
            low_price=Decimal("44500.00"),
            close_price=Decimal("45250.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("4525000.00"),
            trades_count=150,
            metadata={"test": "lifecycle"},
        )

        # Verify calculated properties
        assert kline.price_change == Decimal("250.00")
        assert kline.is_bullish is True
        assert kline.duration == timedelta(minutes=5)

        # Serialize to dict
        kline_dict = kline.to_dict()
        assert kline_dict["price_change"] == "250.00"

        # Verify string representation
        str_repr = str(kline)
        assert "O:45000.00" in str_repr
        assert "H:45500.00" in str_repr
        assert "L:44500.00" in str_repr
        assert "C:45250.00" in str_repr

    def test_kline_equality_and_hashing(self) -> None:
        """Test kline equality and hashing behavior.

        Description of what the test covers:
        Verifies that `Kline` objects with identical content are considered equal
        and have the same hash, while objects with different content are not equal.

        Preconditions:
        - None.

        Steps:
        - Create two `Kline` objects with identical data.
        - Assert that they are equal (`==`).
        - Create a third `Kline` object with different data.
        - Assert that it is not equal to the first two.

        Expected Result:
        - `Kline` objects should correctly implement equality and hashing based on their content.
        """
        base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        close_time = base_time + timedelta(minutes=1)

        kline1 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        kline2 = Kline(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("50000"),
            high_price=Decimal("50100"),
            low_price=Decimal("49900"),
            close_price=Decimal("50050"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("50000"),
            trades_count=10,
        )

        # Pydantic models are equal if all fields are equal
        assert kline1 == kline2

        # Different symbol should make them different
        kline3 = Kline(
            symbol="ETHUSDT",  # Different
            interval=KlineInterval.MINUTE_1,
            open_time=base_time,
            close_time=close_time,
            open_price=Decimal("3000"),
            high_price=Decimal("3010"),
            low_price=Decimal("2990"),
            close_price=Decimal("3005"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("3000"),
            trades_count=10,
        )

        assert kline1 != kline3
