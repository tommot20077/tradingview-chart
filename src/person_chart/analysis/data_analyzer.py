"""
Crypto Data Analyzer - 分析存儲在 InfluxDB 中的加密貨幣數據
提供數據查詢、統計分析和可視化功能
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3

from ..data_models import MarketSummary

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

        Parameters:
            host (str, optional): InfluxDB 服務器的主機位址。若為 None，則從環境變數 'INFLUXDB_HOST' 載入。
            token (str, optional): 用於 InfluxDB 認證的令牌。若為 None，則從環境變數 'INFLUXDB_TOKEN' 載入。
            database (str, optional): 要連接的 InfluxDB 資料庫名稱。若為 None，則從環境變數 'INFLUXDB_DATABASE' 載入。

        Raises:
            ValueError: 如果 InfluxDB 連接參數缺失則拋出。
        """
        self.host = host or os.getenv('INFLUXDB_HOST')
        self.token = token or os.getenv('INFLUXDB_TOKEN')
        self.database = database or os.getenv('INFLUXDB_DATABASE')

        if not all([self.host, self.token, self.database]):
            msg = "InfluxDB 連接參數缺失。請確保 INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE 已在 .env 文件中設定。"
            log.error(msg)
            raise ValueError(msg)

        self.client = InfluxDBClient3(host=self.host, token=self.token, database=self.database)
        log.info(f"CryptoDataAnalyzer 初始化完成，連接到 InfluxDB: {self.host}/{self.database}")

    def get_price_data(self, symbol: str, interval_time: Optional[timedelta] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        獲取指定時間範圍內的價格數據。

        Parameters:
            symbol (str): 加密貨幣符號 (例如 'BTCUSDT')。
            interval_time (timedelta, optional): 從現在回溯的時間間隔。如果提供，將覆蓋 start_time。
            start_time (datetime, optional): 查詢的開始時間 (UTC)。預設為 24 小時前。
            end_time (datetime, optional): 查詢的結束時間 (UTC)。預設為當前時間。

        Returns:
            pd.DataFrame: 包含價格數據的 DataFrame，索引為 'time'。若無數據或出錯則返回空 DataFrame。
        """
        if not symbol:
            log.warning("未提供加密貨幣符號，無法查詢價格數據。")
            return pd.DataFrame()

        now = datetime.now(timezone.utc)
        if interval_time:
            start_time = now - interval_time
            end_time = now
        else:
            start_time = start_time or (now - timedelta(hours=24))
            end_time = end_time or now

        log.info(f"正在獲取 {symbol} 從 {start_time.isoformat()} 到 {end_time.isoformat()} 的價格數據...")

        query = f"""
        SELECT *
        FROM crypto_price
        WHERE symbol = '{symbol.upper()}'
          AND time >= '{start_time.isoformat()}'
          AND time <= '{end_time.isoformat()}'
        ORDER BY time ASC
        """

        try:
            table = self.client.query(query=query, language='sql')
            df = table.to_pandas().set_index('time')
            df.index = pd.to_datetime(df.index)
            log.info(f"成功獲取 {len(df)} 條 {symbol} 的價格數據。")
            return df
        except Exception as e:
            log.error(f"查詢 {symbol} 價格數據時發生錯誤: {e}")
            return pd.DataFrame()

    def calculate_market_summary(self, symbol: str, hours: int = 24) -> Optional[MarketSummary]:
        """
        計算指定加密貨幣在給定時間範圍內的市場摘要統計。

        Parameters:
            symbol (str): 加密貨幣符號。
            hours (int): 回溯的時間範圍（小時），預設為 24。

        Returns:
            Optional[MarketSummary]: 包含市場摘要的 MarketSummary 物件，如果沒有數據則為 None。
        """
        log.info(f"正在計算 {symbol} 在過去 {hours} 小時內的市場摘要...")
        df = self.get_price_data(symbol, interval_time=timedelta(hours=hours))

        if df.empty:
            log.warning(f"沒有足夠的數據來計算 {symbol} 的市場摘要。")
            return None

        try:
            current_price = df['close'].iloc[-1]
            first_price = df['open'].iloc[0]
            price_change_24h = current_price - first_price
            price_change_percent_24h = (price_change_24h / first_price) * 100 if first_price != 0 else 0.0
            volatility = df['close'].pct_change().std() * 100

            summary = MarketSummary(
                symbol=symbol.upper(),
                current_price=current_price,
                price_change_24h=price_change_24h,
                price_change_percent_24h=price_change_percent_24h,
                high_24h=df['high'].max(),
                low_24h=df['low'].min(),
                volume_24h=df['volume'].sum(),
                avg_price_24h=df['close'].mean(),
                volatility=volatility if not np.isnan(volatility) else 0.0
            )
            log.info(f"{symbol} 的市場摘要計算完成。")
            return summary
        except IndexError:
            log.error(f"計算 {symbol} 市場摘要時索引錯誤，數據可能不足。")
            return None
        except Exception as e:
            log.error(f"計算 {symbol} 市場摘要時發生未知錯誤: {e}")
            return None

    def get_available_symbols(self, hours: int = 24) -> List[str]:
        """
        從數據庫中獲取最近指定小時內有數據的可用加密貨幣符號列表。

        Parameters:
            hours (int): 回溯的時間範圍（小時），預設為 24。

        Returns:
            List[str]: 可用符號的列表。
        """
        log.info(f"正在獲取過去 {hours} 小時內活躍的加密貨幣符號...")
        query = f"""
        SELECT DISTINCT(symbol)
        FROM crypto_price
        WHERE time >= now() - interval '{hours} hours'
        """
        try:
            table = self.client.query(query=query, language='sql')
            symbols = [row['symbol'] for row in table.to_arrow().to_pydict()['symbol']]
            log.info(f"找到 {len(symbols)} 個可用符號: {symbols}")
            return symbols
        except Exception as e:
            log.error(f"獲取可用符號時發生錯誤: {e}")
            return []

    def generate_report(self, symbol: str, hours: int = 24) -> Dict:
        """
        為指定加密貨幣在給定時間範圍內生成一份綜合分析報告。

        Parameters:
            symbol (str): 加密貨幣符號。
            hours (int): 時間範圍（小時），預設為 24。

        Returns:
            Dict: 包含完整分析報告的字典。
        """
        log.info(f"正在為 {symbol} 在過去 {hours} 小時內生成綜合分析報告...")
        try:
            market_summary = self.calculate_market_summary(symbol, hours)

            report = {
                'symbol': symbol.upper(),
                'analysis_period_hours': hours,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'market_summary': market_summary.to_dict() if market_summary else None,
                'data_availability': market_summary is not None
            }
            log.info(f"{symbol} 的分析報告生成完成。")
            return report
        except Exception as e:
            log.error(f"生成報告時發生錯誤: {e}")
            return {'error': str(e), 'symbol': symbol.upper()}

    def close(self):
        """
        關閉與 InfluxDB 資料庫的連接。
        """
        log.info("關閉 InfluxDB 客戶端連接...")
        if self.client:
            self.client.close()
            log.info("InfluxDB 客戶端連接已關閉。")


def main():
    """
    主函數 - 演示 CryptoDataAnalyzer 的功能。
    """
    log.info("啟動數據分析器演示...")
    try:
        analyzer = CryptoDataAnalyzer()
        symbols = analyzer.get_available_symbols()

        if not symbols:
            log.warning("在過去 24 小時內未找到任何數據，無法生成報告。")
            log.warning("請先運行 'python run.py --enhanced' 並等待幾分鐘以收集數據。")
            return

        symbol_to_analyze = symbols[0]
        log.info(f"將為第一個可用符號 '{symbol_to_analyze}' 生成報告。")

        report = analyzer.generate_report(symbol_to_analyze, hours=24)

        print("\n" + "=" * 50)
        print(f"📊 {symbol_to_analyze} 的 24 小時分析報告")
        print(f"   報告生成時間: {report['generated_at']}")
        print("=" * 50)

        if report.get('market_summary'):
            summary = report['market_summary']
            print(f"  當前價格: ${summary['current_price']:.4f}")
            print(f"  24小時變動: {summary['price_change_percent_24h']:.2f}% (${summary['price_change_24h']:.4f})")
            print(f"  24小時最高價: ${summary['high_24h']:.4f}")
            print(f"  24小時最低價: ${summary['low_24h']:.4f}")
            print(f"  24小時交易量: {summary['volume_24h']:.2f}")
            print(f"  波動率: {summary['volatility']:.2f}%")
        else:
            print("  無法生成市場摘要，可能數據不足。")

        print("=" * 50)

    except ValueError as e:
        log.error(f"初始化分析器失敗: {e}")
    except Exception as e:
        log.error(f"在分析過程中發生未預期的錯誤: {e}")
    finally:
        if 'analyzer' in locals() and analyzer:
            analyzer.close()
        log.info("數據分析器演示結束。")


if __name__ == "__main__":
    main()
