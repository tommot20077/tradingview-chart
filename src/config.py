import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration loaded from environment variables"""

    # InfluxDB Configuration
    influxdb_host: str
    influxdb_token: str
    influxdb_database: str

    # Binance Configuration
    binance_symbol: str
    binance_interval: str

    # Server Configuration
    api_host: str
    api_port: int

    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            # InfluxDB Configuration
            influxdb_host=os.getenv('INFLUXDB_HOST', 'http://localhost:8086'),
            influxdb_token=os.getenv('INFLUXDB_TOKEN', ''),
            influxdb_database=os.getenv('INFLUXDB_DATABASE', 'crypto_data'),

            # Binance Configuration
            binance_symbol=os.getenv('BINANCE_SYMBOL', 'btcusdt'),
            binance_interval=os.getenv('BINANCE_INTERVAL', '1m'),

            # Server Configuration
            api_host=os.getenv('API_HOST', '127.0.0.1'),
            api_port=int(os.getenv('API_PORT', '8000'))
        )

    def validate(self) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            self.influxdb_host,
            self.influxdb_token,
            self.influxdb_database
        ]

        missing_fields = [field for field in required_fields if not field]

        if missing_fields:
            print(f"Missing required configuration: {missing_fields}")
            return False

        return True


# Global configuration instance
config = Config.from_env()
