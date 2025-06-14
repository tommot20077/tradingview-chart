from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any


class AbstractRealtimeDataProvider(ABC):
    """
    用於獲取即時市場數據的提供者的抽象基礎類別。
    定義了所有即時數據提供者必須實現的通用介面。
    """

    @abstractmethod
    def start(self):
        """
        啟動數據提供者，開始獲取數據。
        """
        pass

    @abstractmethod
    def stop(self):
        """
        停止數據提供者，結束數據獲取。
        """
        pass

    @abstractmethod
    def subscribe(self, symbol: str, **kwargs):
        """
        訂閱特定符號的即時數據流。

        Parameters:
            symbol (str): 要訂閱的交易對符號。
            **kwargs: 其他訂閱參數 (例如 'interval')。
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbol: str, **kwargs):
        """
        取消訂閱特定符號的即時數據流。

        Parameters:
            symbol (str): 要取消訂閱的交易對符號。
            **kwargs: 其他取消訂閱參數。
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """
        獲取提供者的運行統計數據。

        Returns:
            Dict: 包含提供者運行統計數據的字典。
        """
        pass

    @abstractmethod
    def get_latest_prices(self) -> Dict:
        """
        獲取所有已快取符號的最新價格數據。

        Returns:
            Dict: 鍵為符號，值為最新價格數據的字典。
        """
        pass

    @property
    @abstractmethod
    def subscribed_symbols(self) -> List[str]:
        """
        獲取當前已訂閱的符號列表。

        Returns:
            List[str]: 當前已訂閱的符號流名稱列表 (例如 'btcusdt@kline_1m')。
        """
        pass


class AbstractHistoricalDataProvider(ABC):
    """
    用於獲取歷史市場數據的提供者的抽象基礎類別。
    定義了查詢歷史數據的通用介面。
    """

    @abstractmethod
    def get_historical_data(self, symbol: str, start_time: datetime, end_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """
        獲取指定時間範圍和間隔的歷史K線數據。

        Parameters:
            symbol (str): 交易對符號。
            start_time (datetime): 查詢的開始時間。
            end_time (datetime): 查詢的結束時間。
            interval (str): 數據的時間間隔 (例如 '1m', '1h')。

        Returns:
            List[Dict[str, Any]]: 包含歷史K線數據的字典列表。
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """
        獲取數據庫中可用的交易對符號列表。

        Returns:
            List[str]: 可用符號的列表。
        """
        pass
