import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 從 .env 檔案載入環境變數
load_dotenv()


@dataclass
class Config:
    """
    應用程式配置，從環境變數載入。

    屬性:
        influxdb_host (str): InfluxDB 的主機位址。
        influxdb_token (str): InfluxDB 的認證令牌。
        influxdb_database (str): InfluxDB 的資料庫名稱。
        binance_symbol (str): 幣安交易對符號，例如 'btcusdt'。
        binance_interval (str): 幣安 K 線資料的時間間隔，例如 '1m'。
        api_host (str): API 服務器的主機位址。
        api_port (int): API 服務器的埠號。
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

    @classmethod
    def from_env(cls) -> 'Config':
        """
        從環境變數建立配置實例。

        輸入:
            cls (Type[Config]): 類別本身。

        輸出:
            Config: 包含從環境變數載入的配置的 Config 實例。
        """
        logging.info("從環境變數載入配置...")
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
            api_port=int(os.getenv('API_PORT', '8000'))
        )

    def validate(self) -> bool:
        """
        驗證所需的配置是否存在。

        輸入:
            self (Config): Config 實例本身。

        輸出:
            bool: 如果所有必需的配置都存在則為 True，否則為 False。
        """
        logging.info("驗證配置...")
        required_fields = [
            self.influxdb_host,
            self.influxdb_token,
            self.influxdb_database
        ]

        missing_fields = [field for field in required_fields if not field]

        if missing_fields:
            logging.error(f"配置驗證失敗。缺少必需的配置: {missing_fields}")
            return False

        logging.info("配置驗證成功。")
        return True


# 全局配置實例
config = Config.from_env()
