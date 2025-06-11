"""
InfluxDB connection test utility
This file can be used to test InfluxDB connectivity and data writing
"""

import os
from datetime import datetime
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options
from dotenv import load_dotenv
import logging

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 載入環境變數
load_dotenv()


def test_influxdb_connection() -> bool:
    """
    測試 InfluxDB 連接並寫入範例數據。

    此函數從環境變數中獲取 InfluxDB 配置，嘗試連接到資料庫，
    並寫入兩個測試數據點。它還配置了寫入成功、失敗和重試的回調函數。

    輸入:
        無。

    輸出:
        bool: 如果連接和寫入測試成功則為 True，否則為 False。
    """
    logging.info("啟動 InfluxDB 連接測試。")

    # 從環境變數獲取配置
    host = os.getenv('INFLUXDB_HOST')
    token = os.getenv('INFLUXDB_TOKEN')
    database = os.getenv('INFLUXDB_DATABASE')

    if not all([host, token, database]):
        logging.error("錯誤: .env 檔案中缺少 InfluxDB 配置。")
        logging.error("必需: INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE")
        return False

    logging.info(f"正在測試連接到 InfluxDB:")
    logging.info(f"  主機: {host}")
    logging.info(f"  資料庫: {database}")

    # 建立測試數據點
    test_points = [
        Point("crypto_price_test")
        .tag("symbol", "BTCUSDT")
        .tag("source", "test")
        .field("price", 45000.50)
        .field("open", 44800.00)
        .field("high", 45200.00)
        .field("low", 44700.00)
        .field("close", 45000.50)
        .field("volume", 1234.56)
        .time(datetime.now()),

        Point("crypto_price_test")
        .tag("symbol", "ETHUSDT")
        .tag("source", "test")
        .field("price", 3200.75)
        .field("open", 3180.00)
        .field("high", 3220.00)
        .field("low", 3175.00)
        .field("close", 3200.75)
        .field("volume", 987.65)
        .time(datetime.now())
    ]

    # 配置回調函數
    def success_callback(data: str):
        """
        寫入成功時的回調函數。

        輸入:
            data (str): 成功寫入的資料字串。

        輸出:
            無。
        """
        logging.info(f"✅ 成功寫入測試數據到 InfluxDB ({len(data)} 位元組)")

    def error_callback(data: str, exception: InfluxDBError):
        """
        寫入失敗時的回調函數。

        輸入:
            data (str): 寫入失敗的資料字串。
            exception (InfluxDBError): 寫入失敗時的異常。

        輸出:
            無。
        """
        logging.error(f"❌ 寫入測試數據失敗: {exception}")

    def retry_callback(data: str, exception: InfluxDBError):
        """
        寫入重試時的回調函數。

        輸入:
            data (str): 正在重試寫入的資料字串。
            exception (InfluxDBError): 重試時的異常。

        輸出:
            無。
        """
        logging.warning(f"🔄 正在重試寫入到 InfluxDB: {exception}")

    # 配置寫入選項
    write_options = WriteOptions(
        batch_size=10,
        flush_interval=1_000,
        jitter_interval=0,
        retry_interval=5_000,
        max_retries=3,
        max_retry_delay=30_000,
        exponential_base=2
    )

    wco = write_client_options(
        success_callback=success_callback,
        error_callback=error_callback,
        retry_callback=retry_callback,
        write_options=write_options
    )

    try:
        # 測試連接並寫入數據
        with InfluxDBClient3(
                host=host,
                token=token,
                database=database,
                write_client_options=wco
        ) as client:

            logging.info("🔗 成功連接到 InfluxDB")

            # 寫入測試數據點
            logging.info("📝 正在寫入測試數據...")
            client.write(test_points, write_precision='s')

            logging.info("✅ 測試完成成功！")
            return True

    except Exception as e:
        logging.error(f"❌ 連接到 InfluxDB 時發生錯誤: {e}")
        return False


def query_test_data():
    """
    查詢並顯示 InfluxDB 中的測試數據。

    此函數從環境變數中獲取 InfluxDB 配置，連接到資料庫，
    並查詢最近一小時內寫入的測試數據。

    輸入:
        無。

    輸出:
        無。
    """
    logging.info("啟動查詢測試數據。")

    # 從環境變數獲取配置
    host = os.getenv('INFLUXDB_HOST')
    token = os.getenv('INFLUXDB_TOKEN')
    database = os.getenv('INFLUXDB_DATABASE')

    if not all([host, token, database]):
        logging.error("錯誤: 缺少 InfluxDB 配置，無法查詢數據。")
        return

    try:
        with InfluxDBClient3(host=host, token=token, database=database) as client:

            # 查詢最近的測試數據
            query = f"""
            SELECT *
            FROM crypto_price_test
            WHERE time >= now() - interval '1 hour'
            ORDER BY time DESC
            LIMIT 10
            """

            logging.info("🔍 正在查詢最近的測試數據...")
            result = client.query(query=query, language='sql')

            if result:
                logging.info("📊 最近的測試數據:")
                for row in result:
                    logging.info(f"  {row}")
            else:
                logging.info("📭 未找到測試數據。")

    except Exception as e:
        logging.error(f"❌ 查詢數據時發生錯誤: {e}")


if __name__ == "__main__":
    logging.info("InfluxDB 連接測試工具")
    logging.info("=" * 40)

    # 測試連接並寫入
    if test_influxdb_connection():
        logging.info("\n" + "=" * 40)

        # 查詢測試數據
        query_test_data()

    logging.info("\n" + "=" * 40)
    logging.info("測試完成。請檢查您的 InfluxDB 儀表板以查看測試數據。")
