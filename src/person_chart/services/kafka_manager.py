import logging

from person_chart.colored_logging import setup_colored_logging
from src.person_chart.config import config

import logging

from person_chart.colored_logging import setup_colored_logging
from src.person_chart.config import config

log = setup_colored_logging(level=logging.INFO)

_KAFKA_AVAILABLE = True
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:
    KafkaProducer = None
    KafkaConsumer = None
    NoBrokersAvailable = None
    _KAFKA_AVAILABLE = False
    log.warning("kafka-python 未安裝。Kafka 功能將不可用。請運行 'pip install -e .[kafka]' 來安裝。")


class KafkaManager:
    """
    管理 Kafka 連接、生產者和消費者的類。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類負責管理與 Kafka 消息代理的連接，並提供創建 Kafka 生產者和消費者實例的方法。
        它封裝了 Kafka 客戶端的初始化邏輯，包括引導服務器配置和錯誤處理，
        確保應用程式能夠可靠地發送和接收 Kafka 消息。
    """

    def __init__(self, bootstrap_servers: list):
        """
        初始化 KafkaManager。

        參數:
            bootstrap_servers (list): Kafka 代理的伺服器列表。

        Raises:
            RuntimeError: 如果 Kafka 庫未安裝。
        """
        if not _KAFKA_AVAILABLE:
            raise RuntimeError("Kafka 庫未安裝，無法初始化 KafkaManager。")
        self.bootstrap_servers = bootstrap_servers
        log.info(f"KafkaManager 初始化，準備連接到: {bootstrap_servers}。")

    def create_producer(self) -> KafkaProducer:
        """
        建立並返回一個 Kafka 生產者。

        此方法嘗試使用配置的引導服務器列表創建一個 Kafka 生產者實例。
        生產者配置為重試發送消息並等待所有副本確認，以確保消息的可靠性。
        如果無法連接到 Kafka 代理或發生其他錯誤，將記錄錯誤並拋出異常。

        返回:
            KafkaProducer: Kafka 生產者實例。

        Raises:
            NoBrokersAvailable: 如果無法連接到任何 Kafka 代理。
            Exception: 發生其他未知錯誤。
        """
        log.info("正在建立 Kafka 生產者...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                retries=5,
                acks='all'
            )
            log.info("✅ Kafka 生產者建立成功。")
            return producer
        except NoBrokersAvailable:
            log.error(f"❌ 建立 Kafka 生產者失敗：無法連接到任何代理於 {self.bootstrap_servers}。")
            raise
        except Exception as e:
            log.error(f"❌ 建立 Kafka 生產者時發生未知錯誤: {e}。")
            raise

    def create_consumer(self, topic: str, group_id: str) -> KafkaConsumer:
        """
        建立並返回一個 Kafka 消費者。

        此方法嘗試使用配置的引導服務器列表、指定的主題和消費者組 ID 創建一個 Kafka 消費者實例。
        消費者配置為從最新的消息開始消費，並將接收到的消息值解序列化為 UTF-8 字串。
        如果無法連接到 Kafka 代理或發生其他錯誤，將記錄錯誤並拋出異常。

        參數:
            topic (str): 要消費的主題。
            group_id (str): 消費者組 ID。

        返回:
            KafkaConsumer: Kafka 消費者實例。

        Raises:
            NoBrokersAvailable: 如果無法連接到任何 Kafka 代理。
            Exception: 發生其他未知錯誤。
        """
        log.info(f"正在為主題 '{topic}' 和組 '{group_id}' 建立 Kafka 消費者...")
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='latest',
                value_deserializer=lambda v: v.decode('utf-8', errors='ignore')
            )
            log.info(f"✅ Kafka 消費者為主題 '{topic}' 建立成功。")
            return consumer
        except NoBrokersAvailable:
            log.error(f"❌ 建立 Kafka 消費者失敗：無法連接到任何代理於 {self.bootstrap_servers}。")
            raise
        except Exception as e:
            log.error(f"❌ 建立 Kafka 消費者時發生未知錯誤: {e}。")
            raise


# 全局 Kafka 管理器實例
kafka_manager = None
if config.kafka_enabled:
    if _KAFKA_AVAILABLE:
        try:
            kafka_manager = KafkaManager(bootstrap_servers=config.kafka_bootstrap_servers)
        except Exception as e:
            log.error(f"初始化 KafkaManager 失敗: {e}。")
    else:
        log.warning("配置中啟用了 Kafka，但必要的庫未安裝。Kafka 功能將被禁用。")
