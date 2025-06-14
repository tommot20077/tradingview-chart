#!/usr/bin/env python3
"""
Crypto Price Stream 運行腳本
提供多種運行選項和工具，是與本專案互動的推薦入口。
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))


def run_command(command: list):
    """執行一個子進程命令並處理中斷。"""
    process = None
    try:
        process = subprocess.Popen(command)
        process.wait()
    except KeyboardInterrupt:
        log.info("\n⚠️  用戶中斷操作，正在終止進程...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("進程的終止時間過長，強制終止...")
            process.kill()
    except Exception as e:
        log.error(f"\n❌ 執行命令時發生錯誤: {e}")


def run_basic_server():
    """
    運行基本版本的加密貨幣價格串流服務器。
    使用 uvicorn 啟動在 setup.py 中定義的 'person-chart-basic' 入口點。
    """
    log.info("🚀 正在啟動基本版加密貨幣價格串流服務器...")
    command = [sys.executable, "-m", "uvicorn", "person_chart.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload",
               "--reload-dir", "src"]
    run_command(command)


def run_enhanced_server():
    """
    運行增強版本的加密貨幣價格串流服務器。
    使用 uvicorn 啟動在 setup.py 中定義的 'person-chart-enhanced' 入口點。
    """
    log.info("🚀 正在啟動增強版加密貨幣價格串流服務器 (推薦)...")
    command = [sys.executable, "-m", "uvicorn", "person_chart.enhanced_main:app", "--host", "127.0.0.1", "--port", "8000", "--reload",
               "--reload-dir", "src"]
    run_command(command)


def test_influxdb():
    """
    測試與 InfluxDB 資料庫的連接。
    執行 influx-connector.py 腳本。
    """
    log.info("🔧 正在測試 InfluxDB 連接...")
    command = [sys.executable, "-m", "person_chart.tools.influx_connector"]
    run_command(command)


def run_data_analyzer():
    """
    運行數據分析器。
    執行 data_analyzer.py 腳本。
    """
    log.info("📊 正在運行數據分析器...")
    command = [sys.executable, "-m", "person_chart.analysis.data_analyzer"]
    run_command(command)


def install_project():
    """安裝項目為可編輯模式。"""
    log.info("📦 正在以可編輯模式安裝項目核心依賴...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        log.info("✅ 核心依賴安裝成功。")
        log.info("\n可選功能依賴:")
        log.info("  - 如需使用 Kafka，請運行: pip install -e .[kafka]")
        log.info("  - 如需使用 PostgreSQL，請運行: pip install -e .[postgresql]")
    except subprocess.CalledProcessError as e:
        log.error(f"❌ 安裝失敗: {e}")


def check_environment():
    """檢查 .env 文件配置。"""
    log.info("🔍 正在檢查環境配置...")
    env_file = Path('.env')
    if not env_file.exists():
        log.error("❌ .env 文件未找到。請根據 .env.example 創建一個。")
        return False

    from dotenv import dotenv_values
    config = dotenv_values(".env")

    required_vars = ['INFLUXDB_HOST', 'INFLUXDB_TOKEN', 'INFLUXDB_DATABASE']
    missing_vars = [var for var in required_vars if not config.get(var)]

    if missing_vars:
        log.error(f"❌ .env 文件中缺少或為空的環境變數: {', '.join(missing_vars)}")
        return False

    log.info("✅ 環境配置檢查通過。")
    return True


def show_status():
    """顯示項目狀態。"""
    log.info("📋 項目狀態檢查")
    log.info("=" * 50)

    important_files = [
        'setup.py', '.env', 'src/person_chart/main.py', 'src/person_chart/enhanced_main.py',
        'src/person_chart/analysis/data_analyzer.py', 'src/person_chart/config.py', 'static/index.html'
    ]
    log.info("📁 文件狀態:")
    for file_path_str in important_files:
        file_path = Path(file_path_str)
        status = "✅" if file_path.exists() else "❌ (缺失)"
        log.info(f"  {status} {file_path_str}")

    log.info("\n🔧 環境狀態:")
    check_environment()

    log.info("\n📚 可用命令:")
    log.info("  python run.py --install      # 安裝項目依賴 (首次運行必需)")
    log.info("  python run.py --enhanced     # 運行增強版服務器 (帶儀表板)")
    log.info("  python run.py --basic        # 運行基本版服務器")
    log.info("  python run.py --test-db      # 測試 InfluxDB 連接")
    log.info("  python run.py --analyze      # 運行數據分析腳本")
    log.info("  python run.py --status       # 顯示此狀態報告")
    log.info("=" * 50)


def main():
    """主函數。"""
    parser = argparse.ArgumentParser(
        description="Crypto Price Stream 運行工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
示例用法:
  python run.py --install          # 首次運行，安裝項目
  python run.py --enhanced         # 運行帶有 Web 儀表板的增強版服務器
  python run.py --status           # 檢查項目狀態和配置
"""
    )

    parser.add_argument('--enhanced', action='store_true', help='運行增強版服務器（推薦）')
    parser.add_argument('--basic', action='store_true', help='運行基本版服務器')
    parser.add_argument('--test-db', action='store_true', help='測試 InfluxDB 連接')
    parser.add_argument('--analyze', action='store_true', help='運行數據分析器')
    parser.add_argument('--install', action='store_true', help='安裝項目為可編輯模式')
    parser.add_argument('--status', action='store_true', help='檢查項目狀態')

    args = parser.parse_args()

    if not any(vars(args).values()):
        show_status()
        return

    if args.install:
        install_project()
        return

    if args.enhanced or args.basic or args.test_db or args.analyze:
        if not check_environment():
            log.error("\n❌ 環境檢查失敗。請在繼續之前修復 .env 文件中的問題。")
            return

    if args.test_db:
        test_influxdb()
    elif args.analyze:
        run_data_analyzer()
    elif args.enhanced:
        run_enhanced_server()
    elif args.basic:
        run_basic_server()
    elif args.status:
        show_status()


if __name__ == "__main__":
    log.info("🎯 歡迎使用加密貨幣價格串流運行工具")
    log.info("=" * 50)
    main()
