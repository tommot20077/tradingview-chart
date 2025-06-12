"""
Crypto Data Analyzer - 分析存儲在 InfluxDB 中的加密貨幣數據
提供數據查詢、統計分析和可視化功能
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()


class CryptoDataAnalyzer:
    """
    加密貨幣數據分析器。
    用於從 InfluxDB 查詢、分析和報告加密貨幣價格和交易量數據。
    """

    def __init__(self, host: str = None, token: str = None, database: str = None):
        """
        初始化 CryptoDataAnalyzer 實例。

        輸入:
            host (str, optional): InfluxDB 服務器的主機位址。如果為 None，則從環境變數 'INFLUXDB_HOST' 載入。
            token (str, optional): 用於 InfluxDB 認證的令牌。如果為 None，則從環境變數 'INFLUXDB_TOKEN' 載入。
            database (str, optional): 要連接的 InfluxDB 資料庫名稱。如果為 None，則從環境變數 'INFLUXDB_DATABASE' 載入。

        輸出:
            無。

        異常:
            ValueError: 如果 InfluxDB 連接參數缺失則拋出。
        """
        self.host = host or os.getenv('INFLUXDB_HOST')
        self.token = token or os.getenv('INFLUXDB_TOKEN')
        self.database = database or os.getenv('INFLUXDB_DATABASE')

        if not all([self.host, self.token, self.database]):
            logging.error("InfluxDB 連接參數缺失。請確保 INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE 已設定。")
            raise ValueError("InfluxDB 連接參數是必需的。")

        self.client = InfluxDBClient3(
            host=self.host,
            token=self.token,
            database=self.database
        )
        log.info(f"CryptoDataAnalyzer 初始化完成，連接到 InfluxDB: {self.host}/{self.database}")

    def get_price_data(self, symbol: str, hours: int = 24) -> pd.DataFrame:
        """
        獲取指定時間範圍內的價格數據。

        輸入:
            symbol (str): 加密貨幣符號 (例如 'BTCUSDT')。
            hours (int): 時間範圍（小時），預設為 24 小時。

        輸出:
            pd.DataFrame: 包含價格數據的 DataFrame。如果沒有找到數據或發生錯誤，則返回空的 DataFrame。
        """
        log.info(f"獲取 {symbol} 在過去 {hours} 小時內的價格數據...")
        query = f"""
        SELECT *
        FROM crypto_price
        WHERE symbol = '{symbol.upper()}'
          AND time >= now() - interval '{hours} hours'
        ORDER BY time ASC
        """

        try:
            result = self.client.query(query=query, language='sql')
            if result:
                df = pd.DataFrame(result)
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)
                log.info(f"成功獲取 {len(df)} 條 {symbol} 的價格數據。")
                return df
            else:
                log.warning(f"未找到 {symbol} 的數據。")
                return pd.DataFrame()
        except Exception as e:
            log.error(f"查詢價格數據時發生錯誤: {e}")
            return pd.DataFrame()

    def calculate_market_summary(self, symbol: str, hours: int = 24) -> Optional[MarketSummary]:
        """
        計算指定加密貨幣在給定時間範圍內的市場摘要統計。

        輸入:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24 小時。

        輸出:
            Optional[MarketSummary]: 包含市場摘要的 MarketSummary 物件，如果沒有數據則為 None。
        """
        log.info(f"計算 {symbol} 在過去 {hours} 小時內的市場摘要...")
        df = self.get_price_data(symbol, hours)

        if df.empty:
            log.warning(f"沒有足夠的數據來計算 {symbol} 的市場摘要。")
            return None

        try:
            current_price = df['close'].iloc[-1]
            first_price = df['open'].iloc[0]

            price_change_24h = current_price - first_price
            price_change_percent_24h = (price_change_24h / first_price) * 100

            high_24h = df['high'].max()
            low_24h = df['low'].min()
            volume_24h = df['volume'].sum()
            avg_price_24h = df['close'].mean()

            # 計算波動率 (標準差)
            volatility = df['close'].pct_change().std() * 100

            summary = MarketSummary(
                symbol=symbol.upper(),
                current_price=current_price,
                price_change_24h=price_change_24h,
                price_change_percent_24h=volatility if not np.isnan(volatility) else 0.0,
                high_24h=high_24h,
                low_24h=low_24h,
                volume_24h=volume_24h,
                avg_price_24h=avg_price_24h,
                volatility=volatility if not np.isnan(volatility) else 0.0
            )
            log.info(f"{symbol} 的市場摘要計算完成。")
            return summary
        except Exception as e:
            log.error(f"計算 {symbol} 市場摘要時發生錯誤: {e}")
            return None

    def calculate_trading_stats(self, symbol: str, hours: int = 24) -> Optional[TradingStats]:
        """
        計算指定加密貨幣在給定時間範圍內的交易統計數據。

        輸入:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24 小時。

        輸出:
            Optional[TradingStats]: 包含交易統計的 TradingStats 物件，如果沒有數據則為 None。
        """
        log.info(f"計算 {symbol} 在過去 {hours} 小時內的交易統計...")
        df = self.get_price_data(symbol, hours)

        if df.empty:
            log.warning(f"沒有足夠的數據來計算 {symbol} 的交易統計。")
            return None

        try:
            total_trades = len(df)
            avg_volume = df['volume'].mean()
            max_price = df['high'].max()
            min_price = df['low'].min()
            price_range = max_price - min_price

            # 判斷趨勢方向
            first_price = df['close'].iloc[0]
            last_price = df['close'].iloc[-1]
            price_change_percent = ((last_price - first_price) / first_price) * 100

            if price_change_percent > 2:
                trend_direction = 'bullish'
            elif price_change_percent < -2:
                trend_direction = 'bearish'
            else:
                trend_direction = 'sideways'

            stats = TradingStats(
                total_trades=total_trades,
                avg_volume=avg_volume,
                max_price=max_price,
                min_price=min_price,
                price_range=price_range,
                trend_direction=trend_direction
            )
            log.info(f"{symbol} 的交易統計計算完成。")
            return stats
        except Exception as e:
            log.error(f"計算 {symbol} 交易統計時發生錯誤: {e}")
            return None

    def get_price_alerts(self, symbol: str, threshold_percent: float = 5.0, hours: int = 1) -> List[Dict]:
        """
        檢測指定加密貨幣在給定時間範圍內的價格異常波動並生成警報。

        輸入:
            symbol (str): 加密貨幣符號。
            threshold_percent (float): 警報閾值（價格變化百分比），預設為 5.0%。
            hours (int): 檢查時間範圍（小時），預設為 1 小時。

        輸出:
            List[Dict]: 包含警報資訊的字典列表。如果沒有警報或數據不足，則返回空列表。
        """
        log.info(f"檢測 {symbol} 在過去 {hours} 小時內的價格警報 (閾值: {threshold_percent}%) ...")
        df = self.get_price_data(symbol, hours)

        if df.empty or len(df) < 2:
            log.warning(f"沒有足夠的數據來檢測 {symbol} 的價格警報。")
            return []

        alerts = []

        try:
            # 計算價格變化百分比
            df['price_change_pct'] = df['close'].pct_change() * 100

            # 找出超過閾值的變化
            significant_changes = df[abs(df['price_change_pct']) > threshold_percent]

            for timestamp, row in significant_changes.iterrows():
                alert = {
                    'symbol': symbol.upper(),
                    'timestamp': timestamp.isoformat(),
                    'price': row['close'],
                    'change_percent': row['price_change_pct'],
                    'alert_type': 'price_spike' if row['price_change_pct'] > 0 else 'price_drop',
                    'severity': 'high' if abs(row['price_change_pct']) > threshold_percent * 2 else 'medium'
                }
                alerts.append(alert)
                log.info(
                    f"檢測到 {symbol} 價格警報: {alert['alert_type']} {alert['change_percent']:.2f}% at {alert['timestamp']}")

        except Exception as e:
            log.error(f"檢測價格警報時發生錯誤: {e}")

        return alerts

    def get_volume_analysis(self, symbol: str, hours: int = 24) -> Dict:
        """
        分析指定加密貨幣在給定時間範圍內的交易量數據。

        輸入:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24 小時。

        輸出:
            Dict: 包含交易量分析結果的字典。如果沒有數據，則返回空字典。
        """
        log.info(f"分析 {symbol} 在過去 {hours} 小時內的交易量數據...")
        df = self.get_price_data(symbol, hours)

        if df.empty:
            log.warning(f"沒有足夠的數據來分析 {symbol} 的交易量。")
            return {}

        try:
            # 計算量價關係
            volume_stats = {
                'total_volume': df['volume'].sum(),
                'avg_volume': df['volume'].mean(),
                'max_volume': df['volume'].max(),
                'min_volume': df['volume'].min(),
                'volume_std': df['volume'].std(),
                'high_volume_periods': len(df[df['volume'] > df['volume'].mean() + df['volume'].std()]),
                'low_volume_periods': len(df[df['volume'] < df['volume'].mean() - df['volume'].std()])
            }

            # 計算量價相關性
            if len(df) > 1:
                price_change = df['close'].pct_change()
                volume_correlation = np.corrcoef(price_change[1:], df['volume'][1:])[0, 1]
                volume_stats['price_volume_correlation'] = volume_correlation if not np.isnan(
                    volume_correlation) else 0.0
            else:
                volume_stats['price_volume_correlation'] = 0.0
            log.info(f"{symbol} 的交易量分析完成。")
            return volume_stats

        except Exception as e:
            log.error(f"分析交易量時發生錯誤: {e}")
            return {}

    def get_available_symbols(self, limit: int = 50) -> List[str]:
        """
        從數據庫中獲取最近 24 小時內有數據的可用加密貨幣符號列表。

        輸入:
            limit (int): 返回的最大符號數量，預設為 50。

        輸出:
            List[str]: 可用符號的列表。如果沒有找到符號或發生錯誤，則返回空列表。
        """
        log.info(f"獲取數據庫中可用的加密貨幣符號 (限制: {limit})...")
        query = f"""
        SELECT DISTINCT symbol
        FROM crypto_price
        WHERE time >= now() - interval '24 hours'
        LIMIT {limit}
        """

        try:
            result = self.client.query(query=query, language='sql')
            if result:
                symbols = [row['symbol'] for row in result]
                log.info(f"找到 {len(symbols)} 個可用符號。")
                return symbols
            else:
                log.warning("未找到任何可用符號。")
                return []
        except Exception as e:
            log.error(f"獲取可用符號時發生錯誤: {e}")
            return []

    def export_data_to_csv(self, symbol: str, hours: int = 24, filename: str = None) -> str:
        """
        將指定加密貨幣在給定時間範圍內的價格數據導出為 CSV 文件。

        輸入:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24 小時。
            filename (str, optional): 輸出文件名。如果為 None，則自動生成文件名。

        輸出:
            str: 導出文件的完整路徑。

        異常:
            ValueError: 如果沒有可用數據則拋出。
            Exception: 如果導出過程中發生錯誤則拋出。
        """
        log.info(f"將 {symbol} 在過去 {hours} 小時內的數據導出為 CSV 文件...")
        df = self.get_price_data(symbol, hours)

        if df.empty:
            log.error(f"沒有 {symbol} 的數據可供導出。")
            raise ValueError(f"沒有 {symbol} 的數據可供導出。")

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol.lower()}_data_{timestamp}.csv"

        try:
            df.to_csv(filename)
            log.info(f"數據已成功導出到 {filename}")
            return filename
        except Exception as e:
            log.error(f"導出數據時發生錯誤: {e}")
            raise

    def generate_report(self, symbol: str, hours: int = 24) -> Dict:
        """
        為指定加密貨幣在給定時間範圍內生成一份綜合分析報告。
        報告包含市場摘要、交易統計、交易量分析和價格警報。

        輸入:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24 小時。

        輸出:
            Dict: 包含完整分析報告的字典。如果生成報告時發生錯誤，則包含錯誤資訊。
        """
        log.info(f"為 {symbol} 在過去 {hours} 小時內生成綜合分析報告...")
        try:
            market_summary = self.calculate_market_summary(symbol, hours)
            trading_stats = self.calculate_trading_stats(symbol, hours)
            volume_analysis = self.get_volume_analysis(symbol, hours)
            price_alerts = self.get_price_alerts(symbol, threshold_percent=3.0, hours=hours)

            report = {
                'symbol': symbol.upper(),
                'analysis_period_hours': hours,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'market_summary': market_summary.__dict__ if market_summary else None,
                'trading_stats': trading_stats.__dict__ if trading_stats else None,
                'volume_analysis': volume_analysis,
                'price_alerts': price_alerts,
                'data_availability': len(self.get_price_data(symbol, hours)) > 0
            }
            log.info(f"{symbol} 的分析報告生成完成。")
            return report

        except Exception as e:
            log.error(f"生成報告時發生錯誤: {e}")
            return {
                'error': str(e),
                'symbol': symbol.upper(),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    def close(self):
        """
        關閉與 InfluxDB 資料庫的連接。

        輸入:
            self (CryptoDataAnalyzer): CryptoDataAnalyzer 實例本身。

        輸出:
            無。
        """
        log.info("關閉 InfluxDB 客戶端連接...")
        if self.client:
            self.client.close()
            log.info("InfluxDB 客戶端連接已關閉。")
        else:
            log.info("InfluxDB 客戶端未連接，無需關閉。")


def main():
    """
    主函數 - 演示 CryptoDataAnalyzer 的功能。
    它會初始化分析器，獲取可用符號，並為第一個可用符號生成並列印綜合分析報告。
    """
    log.info("啟動數據分析器演示。")
    try:
        analyzer = CryptoDataAnalyzer()

        # 獲取可用符號
        symbols = analyzer.get_available_symbols(limit=5)
        log.info(f"可用符號: {symbols}")

        if symbols:
            # 分析第一個可用符號
            symbol = symbols[0]
            log.info(f"正在分析 {symbol}...")

            # 生成綜合報告
            report = analyzer.generate_report(symbol, hours=24)

            log.info(f"=== {symbol} 的分析報告 ===")

            if 'market_summary' in report and report['market_summary']:
                summary = report['market_summary']
                log.info(f"當前價格: ${summary['current_price']:.4f}")
                log.info(f"24 小時變化: {summary['price_change_percent_24h']:.2f}%")
                log.info(f"24 小時最高: ${summary['high_24h']:.4f}")
                log.info(f"24 小時最低: ${summary['low_24h']:.4f}")
                log.info(f"24 小時交易量: {summary['volume_24h']:.2f}")
                log.info(f"波動率: {summary['volatility']:.2f}%")

            if 'trading_stats' in report and report['trading_stats']:
                stats = report['trading_stats']
                log.info(f"交易統計:")
                log.info(f"總交易筆數: {stats['total_trades']}")
                log.info(f"趨勢方向: {stats['trend_direction']}")
                log.info(f"價格範圍: ${stats['price_range']:.4f}")

            if 'price_alerts' in report and report['price_alerts']:
                log.info(f"價格警報: 找到 {len(report['price_alerts'])} 個警報")
                for alert in report['price_alerts'][:3]:  # 顯示前 3 個警報
                    log.info(f"  - {alert['alert_type']}: {alert['change_percent']:.2f}% at {alert['timestamp']}")
            else:
                log.info("未找到價格警報。")

        analyzer.close()
        log.info("數據分析器演示結束。")

    except Exception as e:
        log.error(f"主函數中發生錯誤: {e}")


if __name__ == "__main__":
    main()
