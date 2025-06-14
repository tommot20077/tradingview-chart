import logging

from src.person_chart.config import config

# 檢查 Kafka 是否可用
_KAFKA_AVAILABLE = True
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    KafkaProducer = None
    KafkaConsumer = None
    NoBrokersAvailable = None
    _KAFKA_AVAILABLE = False
    logging.warning("kafka-python 未安裝。Kafka 功能將不可用。請運行 'pip install -e .[kafka]' 來安裝。")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class KafkaManager:
    """
    管理 Kafka 連接、生產者和消費者的類。
    提供創建 Kafka 客戶端的標準化方法。
    """

    def __init__(self, bootstrap_servers: list):
        """
        初始化 KafkaManager。

        Parameters:
            bootstrap_servers (list): Kafka 代理的伺服器列表。

        Raises:
            RuntimeError: 如果 Kafka 庫未安裝。
        """
        if not _KAFKA_AVAILABLE:
            raise RuntimeError("Kafka 庫未安裝，無法初始化 KafkaManager。")
        self.bootstrap_servers = bootstrap_servers
        log.info(f"KafkaManager 初始化，準備連接到: {bootstrap_servers}")

    def create_producer(self) -> KafkaProducer:
        """
        建立並返回一個 Kafka 生產者。

        Returns:
            KafkaProducer: Kafka 生產者實例。

        Raises:
            NoBrokersAvailable: 如果無法連接到任何 Kafka 代理。
        """
        log.info("正在建立 Kafka 生產者...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                retries=5,
                acks='all'  # 確保消息被所有副本確認
            )
            log.info("✅ Kafka 生產者建立成功。")
            return producer
        except NoBrokersAvailable:
            log.error(f"❌ 建立 Kafka 生產者失敗：無法連接到任何代理於 {self.bootstrap_servers}。")
            raise
        except Exception as e:
            log.error(f"❌ 建立 Kafka 生產者時發生未知錯誤: {e}")
            raise

    def create_consumer(self, topic: str, group_id: str) -> KafkaConsumer:
        """
        建立並返回一個 Kafka 消費者。

        Parameters:
            topic (str): 要消費的主題。
            group_id (str): 消費者組 ID。

        Returns:
            KafkaConsumer: Kafka 消費者實例。

        Raises:
            NoBrokersAvailable: 如果無法連接到任何 Kafka 代理。
        """
        log.info(f"正在為主題 '{topic}' 和組 '{group_id}' 建立 Kafka 消費者...")
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='latest',  # 從最新的消息開始消費
                value_deserializer=lambda v: v.decode('utf-8', errors='ignore')
            )
            log.info(f"✅ Kafka 消費者為主題 '{topic}' 建立成功。")
            return consumer
        except NoBrokersAvailable:
            log.error(f"❌ 建立 Kafka 消費者失敗：無法連接到任何代理於 {self.bootstrap_servers}。")
            raise
        except Exception as e:
            log.error(f"❌ 建立 Kafka 消費者時發生未知錯誤: {e}")
            raise


# 全局 Kafka 管理器實例
kafka_manager = None
if config.kafka_enabled:
    if _KAFKA_AVAILABLE:
        try:
            kafka_manager = KafkaManager(bootstrap_servers=config.kafka_bootstrap_servers)
        except Exception as e:
            log.error(f"初始化 KafkaManager 失敗: {e}")
    else:
        log.warning("配置中啟用了 Kafka，但必要的庫未安裝。Kafka 功能將被禁用。")
