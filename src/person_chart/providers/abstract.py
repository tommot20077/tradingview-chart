from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any


class AbstractRealtimeDataProvider(ABC):
    """
    用於獲取即時市場數據的提供者的抽象基礎類別。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此抽象基礎類別定義了所有即時數據提供者必須實現的通用介面。
        它確保了不同數據源（如加密貨幣交易所的 WebSocket）
        能夠以統一的方式啟動、停止、訂閱和取消訂閱數據流，
        並提供獲取運行統計和最新價格的方法，便於集成和管理。
    """

    @abstractmethod
    def start(self):
        """
        啟動數據提供者，開始獲取數據。
        此抽象方法應在具體實現中包含啟動數據流（例如 WebSocket 連接）的邏輯。
        """
        pass

    @abstractmethod
    def stop(self):
        """
        停止數據提供者，結束數據獲取。
        此抽象方法應在具體實現中包含停止數據流（例如關閉 WebSocket 連接）的邏輯。
        """
        pass

    @abstractmethod
    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱特定符號的即時數據流。

        此抽象方法應在具體實現中包含訂閱指定交易對實時數據的邏輯。
        可以通過 `kwargs` 傳遞額外的訂閱參數，例如 K 線的時間間隔。

        參數:
            symbol (str): 要訂閱的交易對符號。
            **kwargs: 其他訂閱參數 (例如 'interval')。
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱特定符號的即時數據流。

        此抽象方法應在具體實現中包含取消訂閱指定交易對實時數據的邏輯。
        可以通過 `kwargs` 傳遞額外的取消訂閱參數。

        參數:
            symbol (str): 要取消訂閱的交易對符號。
            **kwargs: 其他取消訂閱參數。
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """
        獲取提供者的運行統計數據。

        此抽象方法應在具體實現中返回一個字典，
        包含數據提供者的運行狀態、性能指標和任何其他相關統計信息。

        返回:
            Dict: 包含提供者運行統計數據的字典。
        """
        pass

    @abstractmethod
    def get_latest_prices(self) -> Dict:
        """
        獲取所有已快取符號的最新價格數據。

        此抽象方法應在具體實現中返回一個字典，
        其中鍵為交易對符號，值為該符號的最新價格數據。
        這通常用於獲取當前緩存中的最新市場快照。

        返回:
            Dict: 鍵為符號，值為最新價格數據的字典。
        """
        pass

    @property
    @abstractmethod
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號列表。

        此抽象屬性應在具體實現中返回一個列表，
        包含所有當前正在訂閱的數據流名稱（例如 'btcusdt@kline_1m'）。

        返回:
            List[str]: 當前已訂閱的符號流名稱列表 (例如 'btcusdt@kline_1m')。
        """
        pass


class AbstractHistoricalDataProvider(ABC):
    """
    用於獲取歷史市場數據的提供者的抽象基礎類別。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此抽象基礎類別定義了所有歷史數據提供者必須實現的通用介面。
        它確保了不同數據源能夠以統一的方式查詢歷史 K 線數據，
        並提供獲取數據庫中可用交易對列表的方法，便於數據回溯和分析。
    """

    @abstractmethod
    def get_historical_data(self, symbol: str, interval: str, start: datetime, end: datetime, limit: int, offset: int) -> List[
        Dict[str, Any]]:
        """
        獲取指定時間範圍和間隔的歷史K線數據。

        此抽象方法應在具體實現中包含從數據源查詢歷史 K 線數據的邏輯。
        查詢結果應支持時間範圍、K 線間隔、數據點數量限制和偏移量等參數，
        並以字典列表的形式返回。

        參數:
            symbol (str): 交易對符號。
            interval (str): K線間隔 (例如 '1m', '5m', '1h', '1d')。
            start (datetime): 查詢的起始時間。
            end (datetime): 查詢的結束時間。
            limit (int): 返回的最大數據點數量。
            offset (int): 偏移量，用於分頁查詢。

        返回:
            List[Dict[str, Any]]: 包含歷史K線數據的字典列表。
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """
        獲取數據庫中可用的交易對符號列表。

        此抽象方法應在具體實現中返回一個列表，
        包含數據庫中所有可用的交易對符號。

        返回:
            List[str]: 可用符號的列表。
        """
        pass
