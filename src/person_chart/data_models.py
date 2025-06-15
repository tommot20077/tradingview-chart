import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from person_chart.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)


@dataclass
class PriceData:
    """
    用於儲存加密貨幣價格資料的資料類別。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此資料類別定義了加密貨幣價格數據的結構，包括交易對符號、
        當前價格、時間戳記以及 K 線的開盤價、最高價、最低價、收盤價和交易量。
        它還可選地包含價格變化量、價格變化百分比和交易數量，
        並提供將實例轉換為字典的方法，以便於 JSON 序列化和數據傳輸。

    Attributes:
        symbol (str): 交易對符號 (例如 'BTCUSDT')。
        price (float): 當前價格 (通常是收盤價)。
        timestamp (datetime): 資料的時間戳記。
        open_price (float): K 線的開盤價。
        high_price (float): K 線的最高價。
        low_price (float): K 線的最低價。
        close_price (float): K 線的收盤價。
        volume (float): K 線的交易量。
        price_change (Optional[float]): 相對於前一個價格的變化量。
        price_change_percent (Optional[float]): 相對於前一個價格的變化百分比。
        trade_count (Optional[int]): K 線期間的交易數量。
    """
    symbol: str
    price: float
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    trade_count: Optional[int] = None

    def to_dict(self) -> dict:
        """
        將 PriceData 物件轉換為字典，以便進行 JSON 序列化。

        此方法將 PriceData 實例的所有屬性轉換為字典，
        並將 datetime 類型的 timestamp 屬性轉換為 ISO 格式的字串，
        以便於數據的序列化和跨系統傳輸。

        返回:
            dict: 包含價格資料的字典，時間戳記已轉換為 ISO 格式字串。
        """
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class InfluxDBStats:
    """
    InfluxDB 操作統計數據結構。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此資料類別用於記錄與 InfluxDB 數據庫交互的統計信息，
        包括總寫入點數、成功寫入批次數、失敗寫入批次數、
        最後一次成功寫入的時間以及寫入重試的次數。
        這些統計數據有助於監控 InfluxDB 數據寫入操作的性能和可靠性。

    Attributes:
        total_writes (int): 總寫入點數。
        successful_writes (int): 成功寫入的批次數。
        failed_writes (int): 寫入失敗的批次數。
        last_write_time (Optional[datetime]): 最後一次成功寫入的時間。
        retry_count (int): 寫入重試的次數。
    """
    total_writes: int = 0
    successful_writes: int = 0
    failed_writes: int = 0
    last_write_time: Optional[datetime] = None
    retry_count: int = 0


@dataclass
class MarketSummary:
    """
    市場摘要數據結構。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此資料類別定義了市場摘要數據的結構，用於提供加密貨幣市場的概覽信息。
        它包含了交易對符號、當前價格、24小時價格變化、最高價、最低價、
        交易量、平均價格以及波動率等關鍵指標，
        並提供將實例轉換為字典的方法。

    Attributes:
        symbol (str): 加密貨幣符號。
        current_price (float): 當前價格。
        price_change_24h (float): 24 小時價格變化量。
        price_change_percent_24h (float): 24 小時價格變化百分比。
        high_24h (float): 24 小時內最高價格。
        low_24h (float): 24 小時內最低價格。
        volume_24h (float): 24 小時交易量。
        avg_price_24h (float): 24 小時平均價格。
        volatility (float): 波動率 (收盤價回報率的標準差)。
    """
    symbol: str
    current_price: float
    price_change_24h: float
    price_change_percent_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    avg_price_24h: float
    volatility: float

    def to_dict(self) -> dict:
        """
        將 MarketSummary 物件轉換為字典。
        此方法將 MarketSummary 實例的所有屬性轉換為字典，
        以便於數據的序列化和傳輸。
        """
        return asdict(self)


@dataclass
class TradingStats:
    """
    交易統計數據結構。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此資料類別定義了交易統計數據的結構，用於提供交易活動的詳細統計信息。
        它包含了總交易筆數、平均交易量、期間內最高價、最低價、價格範圍以及趨勢方向等指標，
        並提供將實例轉換為字典的方法。

    Attributes:
        total_trades (int): 總交易筆數。
        avg_volume (float): 平均交易量。
        max_price (float): 期間內最高價格。
        min_price (float): 期間內最低價格。
        price_range (float): 價格範圍 (最高價 - 最低價)。
        trend_direction (str): 趨勢方向 ('bullish', 'bearish', 'sideways')。
    """
    total_trades: int
    avg_volume: float
    max_price: float
    min_price: float
    price_range: float
    trend_direction: str

    def to_dict(self) -> dict:
        """
        將 TradingStats 物件轉換為字典。
        此方法將 TradingStats 實例的所有屬性轉換為字典，
        以便於數據的序列化和傳輸。
        """
        return asdict(self)
