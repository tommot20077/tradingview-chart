import logging

from kafka import KafkaProducer, KafkaConsumer

from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class KafkaManager:
    """管理 Kafka 連接、生產者和消費者的類。"""

    def __init__(self, bootstrap_servers: list):
        self.bootstrap_servers = bootstrap_servers
        log.info(f"KafkaManager 初始化，連接到: {bootstrap_servers}")

    def create_producer(self) -> KafkaProducer:
        """
        建立並返回一個 Kafka 生產者。

        輸出:
            KafkaProducer: Kafka 生產者實例。

        異常:
            Exception: 如果無法連接到 Kafka，則拋出異常。
        """
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: v.encode('utf-8'),
                retries=5,
                acks='all'
            )
            log.info("Kafka 生產者建立成功。")
            return producer
        except Exception as e:
            log.error(f"建立 Kafka 生產者失敗: {e}")
            raise

    def create_consumer(self, topic: str, group_id: str) -> KafkaConsumer:
        """
        建立並返回一個 Kafka 消費者。

        輸入:
            topic (str): 要消費的主題。
            group_id (str): 消費者組 ID。

        輸出:
            KafkaConsumer: Kafka 消費者實例。

        異常:
            Exception: 如果無法建立消費者，則拋出異常。
        """
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='latest',  # 從最新的消息開始消費
                value_deserializer=lambda v: v.decode('utf-8')
            )
            log.info(f"Kafka 消費者為主題 '{topic}' 和組 '{group_id}' 建立成功。")
            return consumer
        except Exception as e:
            log.error(f"建立 Kafka 消費者失敗: {e}")
            raise


kafka_manager = None
if config.kafka_enabled:
    kafka_manager = KafkaManager(bootstrap_servers=config.kafka_bootstrap_servers)
