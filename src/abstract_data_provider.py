from abc import ABC, abstractmethod
from typing import Dict, List


class AbstractDataProvider(ABC):
    """
    用於獲取即時市場數據的提供者的抽象基礎類別。
    定義了所有數據提供者（例如加密貨幣、股票）必須實現的通用介面。
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
        """訂閱特定符號的數據流。"""
        pass

    @abstractmethod
    def unsubscribe(self, symbol: str, **kwargs):
        """取消訂閱特定符號的數據流。"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """獲取提供者的運行統計數據。"""
        pass

    @abstractmethod
    def get_latest_prices(self) -> Dict:
        """獲取所有已快取符號的最新價格數據。"""
        pass

    @property
    @abstractmethod
    def subscribed_symbols(self) -> List[str]:
        """獲取當前已訂閱的符號列表。"""
        pass
