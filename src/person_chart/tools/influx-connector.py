"""
InfluxDB 連接測試工具
"""
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError

from person_chart.utils.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)

load_dotenv()


def test_influxdb_connection() -> bool:
    """
    測試 InfluxDB 連接並寫入範例數據。

    此函數會從環境變數中獲取 InfluxDB 的連接設定，
    然後嘗試建立與 InfluxDB 的連接。
    如果連接成功，它會寫入一個測試數據點，並嘗試查詢該數據點，
    以驗證寫入和讀取操作是否正常。
    任何連接或操作失敗都會被記錄並返回 False。

    返回:
        bool: 如果連接和寫入測試成功則為 True，否則為 False。
    """
    log.info("正在啟動 InfluxDB 連接測試。")
    host = os.getenv('INFLUXDB_HOST')
    token = os.getenv('INFLUXDB_TOKEN')
    database = os.getenv('INFLUXDB_DATABASE')

    if not all([host, token, database]):
        log.error("錯誤: .env 檔案中缺少 InfluxDB 設定 (INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE)。")
        return False

    log.info(f"正在測試連接到 InfluxDB: {host}, 資料庫: {database}。")

    try:
        with InfluxDBClient3(host=host, token=token, database=database) as client:
            log.info("🔗 成功連接到 InfluxDB。")

            point = (Point("test_measurement")
                     .tag("location", "test")
                     .field("value", 1.0)
                     .time(datetime.now()))

            log.info("📝 正在寫入一個測試數據點...")
            client.write(point)
            log.info("✅ 成功寫入測試數據。")

            log.info("🔍 正在查詢剛寫入的數據...")
            query = "SELECT * FROM test_measurement ORDER BY time DESC LIMIT 1"
            reader = client.query(query=query, language='sql')

            df = reader.to_pandas()
            if not df.empty:
                log.info("✅ 成功查詢到測試數據:")
                log.info(df.to_string())
            else:
                log.warning("⚠️ 未能查詢到剛寫入的數據，請檢查 InfluxDB。")

            return True
    except InfluxDBError as e:
        log.error(f"❌ InfluxDB 操作失敗: {e}。")
        if e.response.status == 401:
            log.error("   (提示: 401 Unauthorized 錯誤通常表示 INFLUXDB_TOKEN 無效或權限不足。)")
        elif e.response.status == 404:
            log.error(f"   (提示: 404 Not Found 錯誤可能表示資料庫/Bucket '{database}' 不存在。)")
    except Exception as e:
        log.error(f"❌ 連接到 InfluxDB 時發生未知錯誤: {e}。")

    return False


def main():
    """
    主函數入口點。
    此函數作為 InfluxDB 連接測試工具的入口點，
    它會調用 `test_influxdb_connection` 函數來執行測試，
    並根據測試結果打印相應的成功或失敗信息。
    """
    log.info("=" * 40)
    log.info("InfluxDB 連接測試工具")
    log.info("=" * 40)
    if test_influxdb_connection():
        log.info("\n🎉 InfluxDB 連接測試成功！")
    else:
        log.error("\n🔥 InfluxDB 連接測試失敗。")
    log.info("=" * 40)


if __name__ == "__main__":
    main()
