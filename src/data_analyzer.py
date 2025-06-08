"""
Crypto Data Analyzer - 分析存儲在 InfluxDB 中的加密貨幣數據
提供數據查詢、統計分析和可視化功能
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from influxdb_client_3 import InfluxDBClient3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class MarketSummary:
    """市場摘要數據結構"""
    symbol: str
    current_price: float
    price_change_24h: float
    price_change_percent_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    avg_price_24h: float
    volatility: float  # 波動率

@dataclass
class TradingStats:
    """交易統計數據結構"""
    total_trades: int
    avg_volume: float
    max_price: float
    min_price: float
    price_range: float
    trend_direction: str  # 'bullish', 'bearish', 'sideways'

class CryptoDataAnalyzer:
    """加密貨幣數據分析器"""
    
    def __init__(self, host: str = None, token: str = None, database: str = None):
        self.host = host or os.getenv('INFLUXDB_HOST')
        self.token = token or os.getenv('INFLUXDB_TOKEN')
        self.database = database or os.getenv('INFLUXDB_DATABASE')
        
        if not all([self.host, self.token, self.database]):
            raise ValueError("InfluxDB connection parameters are required")
        
        self.client = InfluxDBClient3(
            host=self.host,
            token=self.token,
            database=self.database
        )
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_price_data(self, symbol: str, hours: int = 24) -> pd.DataFrame:
        """
        獲取指定時間範圍內的價格數據
        
        Args:
            symbol: 加密貨幣符號 (e.g., 'BTCUSDT')
            hours: 時間範圍（小時）
            
        Returns:
            DataFrame with price data
        """
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
                return df
            else:
                self.logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error querying price data: {e}")
            return pd.DataFrame()

    def calculate_market_summary(self, symbol: str, hours: int = 24) -> Optional[MarketSummary]:
        """
        計算市場摘要統計
        
        Args:
            symbol: 加密貨幣符號
            hours: 時間範圍（小時）
            
        Returns:
            MarketSummary object or None
        """
        df = self.get_price_data(symbol, hours)
        
        if df.empty:
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
            
            return MarketSummary(
                symbol=symbol.upper(),
                current_price=current_price,
                price_change_24h=price_change_24h,
                price_change_percent_24h=price_change_percent_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                volume_24h=volume_24h,
                avg_price_24h=avg_price_24h,
                volatility=volatility if not np.isnan(volatility) else 0.0
            )
        except Exception as e:
            self.logger.error(f"Error calculating market summary: {e}")
            return None

    def calculate_trading_stats(self, symbol: str, hours: int = 24) -> Optional[TradingStats]:
        """
        計算交易統計數據
        
        Args:
            symbol: 加密貨幣符號
            hours: 時間範圍（小時）
            
        Returns:
            TradingStats object or None
        """
        df = self.get_price_data(symbol, hours)
        
        if df.empty:
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
            
            return TradingStats(
                total_trades=total_trades,
                avg_volume=avg_volume,
                max_price=max_price,
                min_price=min_price,
                price_range=price_range,
                trend_direction=trend_direction
            )
        except Exception as e:
            self.logger.error(f"Error calculating trading stats: {e}")
            return None

    def get_price_alerts(self, symbol: str, threshold_percent: float = 5.0, hours: int = 1) -> List[Dict]:
        """
        檢測價格異常波動（警報）
        
        Args:
            symbol: 加密貨幣符號
            threshold_percent: 警報閾值（百分比）
            hours: 檢查時間範圍（小時）
            
        Returns:
            List of alert dictionaries
        """
        df = self.get_price_data(symbol, hours)
        
        if df.empty or len(df) < 2:
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
                
        except Exception as e:
            self.logger.error(f"Error detecting price alerts: {e}")
        
        return alerts

    def get_volume_analysis(self, symbol: str, hours: int = 24) -> Dict:
        """
        分析交易量數據
        
        Args:
            symbol: 加密貨幣符號
            hours: 時間範圍（小時）
            
        Returns:
            Volume analysis dictionary
        """
        df = self.get_price_data(symbol, hours)
        
        if df.empty:
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
                volume_stats['price_volume_correlation'] = volume_correlation if not np.isnan(volume_correlation) else 0.0
            else:
                volume_stats['price_volume_correlation'] = 0.0
            
            return volume_stats
            
        except Exception as e:
            self.logger.error(f"Error analyzing volume: {e}")
            return {}

    def get_available_symbols(self, limit: int = 50) -> List[str]:
        """
        獲取數據庫中可用的加密貨幣符號
        
        Args:
            limit: 返回的最大符號數量
            
        Returns:
            List of available symbols
        """
        query = f"""
        SELECT DISTINCT symbol
        FROM crypto_price
        WHERE time >= now() - interval '24 hours'
        LIMIT {limit}
        """
        
        try:
            result = self.client.query(query=query, language='sql')
            if result:
                return [row['symbol'] for row in result]
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error getting available symbols: {e}")
            return []

    def export_data_to_csv(self, symbol: str, hours: int = 24, filename: str = None) -> str:
        """
        將數據導出為 CSV 文件
        
        Args:
            symbol: 加密貨幣符號
            hours: 時間範圍（小時）
            filename: 輸出文件名（可選）
            
        Returns:
            文件路徑
        """
        df = self.get_price_data(symbol, hours)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol.lower()}_data_{timestamp}.csv"
        
        try:
            df.to_csv(filename)
            self.logger.info(f"Data exported to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            raise

    def generate_report(self, symbol: str, hours: int = 24) -> Dict:
        """
        生成綜合分析報告
        
        Args:
            symbol: 加密貨幣符號
            hours: 時間範圍（小時）
            
        Returns:
            Complete analysis report
        """
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
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return {
                'error': str(e),
                'symbol': symbol.upper(),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    def close(self):
        """關閉數據庫連接"""
        if self.client:
            self.client.close()


def main():
    """主函數 - 演示分析器功能"""
    try:
        analyzer = CryptoDataAnalyzer()
        
        # 獲取可用符號
        symbols = analyzer.get_available_symbols(limit=5)
        print(f"Available symbols: {symbols}")
        
        if symbols:
            # 分析第一個可用符號
            symbol = symbols[0]
            print(f"\nAnalyzing {symbol}...")
            
            # 生成綜合報告
            report = analyzer.generate_report(symbol, hours=24)
            
            print(f"\n=== Analysis Report for {symbol} ===")
            
            if 'market_summary' in report and report['market_summary']:
                summary = report['market_summary']
                print(f"Current Price: ${summary['current_price']:.4f}")
                print(f"24h Change: {summary['price_change_percent_24h']:.2f}%")
                print(f"24h High: ${summary['high_24h']:.4f}")
                print(f"24h Low: ${summary['low_24h']:.4f}")
                print(f"24h Volume: {summary['volume_24h']:.2f}")
                print(f"Volatility: {summary['volatility']:.2f}%")
            
            if 'trading_stats' in report and report['trading_stats']:
                stats = report['trading_stats']
                print(f"\nTrading Stats:")
                print(f"Total Trades: {stats['total_trades']}")
                print(f"Trend Direction: {stats['trend_direction']}")
                print(f"Price Range: ${stats['price_range']:.4f}")
            
            if 'price_alerts' in report and report['price_alerts']:
                print(f"\nPrice Alerts: {len(report['price_alerts'])} alerts found")
                for alert in report['price_alerts'][:3]:  # Show first 3 alerts
                    print(f"  - {alert['alert_type']}: {alert['change_percent']:.2f}% at {alert['timestamp']}")
        
        analyzer.close()
        
    except Exception as e:
        print(f"Error in main: {e}")


if __name__ == "__main__":
    main()
