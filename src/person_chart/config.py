import logging
import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

from person_chart.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)

# 從 .env 檔案載入環境變數
load_dotenv()


@dataclass
class Config:
    """
    應用程式設定，從環境變數載入。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類用於管理應用程式的所有配置設定，這些設定主要從環境變數中載入。
        它包含了 InfluxDB、幣安、API 服務器、Kafka 和資料庫等相關設定，
        並提供了一個從環境變數創建實例的方法以及一個設定驗證方法，
        確保應用程式在啟動前擁有正確且完整的運行環境。

    Attributes:
        influxdb_host (str): InfluxDB 的主機位址。
        influxdb_token (str): InfluxDB 的認證令牌。
        influxdb_database (str): InfluxDB 的資料庫名稱。
        binance_base_interval: (str): 幣安 K 線資料的基礎時間間隔，例如 '1m'。
        binance_aggregation_intervals: List[str]: 幣安 K 線資料的聚合時間間隔列表，例如 ['1m', '5m', '15m', '1h', '1d']。
        api_host (str): API 服務器的主機位址。
        api_port (int): API 服務器的埠號。
        kafka_enabled (bool): 是否啟用 Kafka 消息隊列。
        kafka_bootstrap_servers (List[str]): Kafka 服務器的引導位址列表。
        kafka_topic (str): Kafka 用於發布價格數據的主題名稱。
        db_type (str): 資料庫類型 ('sqlite' 或 'postgresql')。
        db_path (str): SQLite 資料庫文件的路徑 (僅適用於 SQLite)。
        db_url (str): PostgreSQL 資料庫的連接 URL (僅適用於 PostgreSQL)。
    """

    # InfluxDB 設定
    influxdb_host: str
    influxdb_token: str
    influxdb_database: str

    # 幣安設定
    binance_base_interval: str
    binance_aggregation_intervals: List[str]

    # 服務器設定
    api_host: str
    api_port: int

    # Kafka 設定
    kafka_enabled: bool
    kafka_bootstrap_servers: List[str]
    kafka_topic: str

    # 資料庫設定
    db_type: str
    db_path: str
    db_url: str

    @classmethod
    def from_env(cls) -> 'Config':
        """
        從環境變數建立配置實例。

        此類方法會從系統環境變數中讀取所有必要的配置參數，
        並將其封裝為一個 Config 實例。
        如果某些環境變數未設置，則會使用預設值。

        返回:
            Config: 包含從環境變數載入的配置的 Config 實例。
        """
        log.info("從環境變數載入設定...")

        agg_intervals_str = os.getenv('BINANCE_AGGREGATION_INTERVALS', '5m,15m,30m,1h,4h,12h,1d,1w,1M,1y')
        aggregation_intervals = [s.strip() for s in agg_intervals_str.split(',')]

        return cls(
            influxdb_host=os.getenv('INFLUXDB_HOST', 'http://localhost:8086'),
            influxdb_token=os.getenv('INFLUXDB_TOKEN', ''),
            influxdb_database=os.getenv('INFLUXDB_DATABASE', 'crypto_data'),

            binance_base_interval=os.getenv('BINANCE_BASE_INTERVAL', '1m'),
            binance_aggregation_intervals=aggregation_intervals,

            api_host=os.getenv('API_HOST', '127.0.0.1'),
            api_port=int(os.getenv('API_PORT', '8000')),

            kafka_enabled=os.getenv('KAFKA_ENABLED', 'false').lower() == 'true',
            kafka_bootstrap_servers=[s.strip() for s in os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')],
            kafka_topic=os.getenv('KAFKA_TOPIC', 'crypto-prices'),

            db_type=os.getenv('DB_TYPE', 'sqlite'),
            db_path=os.getenv('DB_PATH', './sqlite.db'),
            db_url=os.getenv('DB_URL', '')
        )

    def validate(self) -> bool:
        """
        驗證所需的設定是否存在。

        此方法會檢查所有必要的配置參數是否已正確設置且不為空。
        如果發現任何缺失或不正確的配置，將會記錄錯誤訊息並返回 False。
        特別針對 Kafka 和 PostgreSQL 的啟用情況進行額外檢查。

        返回:
            bool: 如果所有必需的配置都存在且有效則為 True，否則為 False。
        """
        log.info("正在驗證設定...")
        required_fields = {
            'INFLUXDB_HOST': self.influxdb_host,
            'INFLUXDB_TOKEN': self.influxdb_token,
            'INFLUXDB_DATABASE': self.influxdb_database
        }

        missing_fields = [name for name, value in required_fields.items() if not value]
        if missing_fields:
            log.error(f"配置驗證失敗。缺少必需的配置: {', '.join(missing_fields)}")
            return False

        if self.kafka_enabled:
            if not self.kafka_bootstrap_servers or not self.kafka_topic:
                log.error("Kafka 已啟用，但 KAFKA_BOOTSTRAP_SERVERS 或 KAFKA_TOPIC 未設定。")
                return False

        if self.db_type not in ['sqlite', 'postgresql']:
            log.error(f"不支援的資料庫類型: {self.db_type}。請使用 'sqlite' 或 'postgresql'。")
            return False

        if self.db_type == 'postgresql' and not self.db_url:
            log.error("DB_TYPE 設為 'postgresql'，但 DB_URL 未設定。")
            return False

        log.info("配置驗證成功。")
        return True


# 全局配置實例
config = Config.from_env()
