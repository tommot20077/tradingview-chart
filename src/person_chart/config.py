import os
from dataclasses import dataclass
from typing import List
import logging

from dotenv import load_dotenv

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# 從 .env 檔案載入環境變數
load_dotenv()


@dataclass
class Config:
    """
    應用程式配置，從環境變數載入。

    Attributes:
        influxdb_host (str): InfluxDB 的主機位址。
        influxdb_token (str): InfluxDB 的認證令牌。
        influxdb_database (str): InfluxDB 的資料庫名稱。
        binance_symbol (str): 幣安交易對符號，例如 'btcusdt'。
        binance_interval (str): 幣安 K 線資料的時間間隔，例如 '1m'。
        api_host (str): API 服務器的主機位址。
        api_port (int): API 服務器的埠號。
        kafka_enabled (bool): 是否啟用 Kafka 消息隊列。
        kafka_bootstrap_servers (List[str]): Kafka 服務器的引導位址列表。
        kafka_topic (str): Kafka 用於發布價格數據的主題名稱。
        db_type (str): 資料庫類型 ('sqlite' 或 'postgresql')。
        db_path (str): SQLite 資料庫文件的路徑 (僅適用於 SQLite)。
        db_url (str): PostgreSQL 資料庫的連接 URL (僅適用於 PostgreSQL)。
    """

    # InfluxDB 配置
    influxdb_host: str
    influxdb_token: str
    influxdb_database: str

    # 幣安配置
    binance_symbol: str
    binance_interval: str

    # 服務器配置
    api_host: str
    api_port: int

    # Kafka 配置
    kafka_enabled: bool
    kafka_bootstrap_servers: List[str]
    kafka_topic: str

    # 資料庫配置
    db_type: str
    db_path: str
    db_url: str

    @classmethod
    def from_env(cls) -> 'Config':
        """
        從環境變數建立配置實例。

        Returns:
            Config: 包含從環境變數載入的配置的 Config 實例。
        """
        log.info("從環境變數載入配置...")
        return cls(
            # InfluxDB 配置
            influxdb_host=os.getenv('INFLUXDB_HOST', 'http://localhost:8086'),
            influxdb_token=os.getenv('INFLUXDB_TOKEN', ''),
            influxdb_database=os.getenv('INFLUXDB_DATABASE', 'crypto_data'),

            # 幣安配置
            binance_symbol=os.getenv('BINANCE_SYMBOL', 'btcusdt'),
            binance_interval=os.getenv('BINANCE_INTERVAL', '1m'),

            # 服務器配置
            api_host=os.getenv('API_HOST', '127.0.0.1'),
            api_port=int(os.getenv('API_PORT', '8000')),

            # Kafka 配置
            kafka_enabled=os.getenv('KAFKA_ENABLED', 'false').lower() == 'true',
            kafka_bootstrap_servers=[s.strip() for s in os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')],
            kafka_topic=os.getenv('KAFKA_TOPIC', 'crypto-prices'),

            # 資料庫配置
            db_type=os.getenv('DB_TYPE', 'sqlite'),
            db_path=os.getenv('DB_PATH', './sqlite.db'),
            db_url=os.getenv('DB_URL', '')
        )

    def validate(self) -> bool:
        """
        驗證所需的配置是否存在。

        Returns:
            bool: 如果所有必需的配置都存在則為 True，否則為 False。
        """
        log.info("驗證配置...")
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
