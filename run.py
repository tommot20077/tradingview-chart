#!/usr/bin/env python3
"""
Crypto Price Stream 運行腳本
提供多種運行選項和工具
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(message)s')


def run_basic_server():
    """
    運行基本版本的加密貨幣價格串流服務器。

    此函數會啟動位於 `./src/main.py` 的基本服務器，該服務器負責獲取和處理加密貨幣價格數據。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("🚀 正在啟動基本版加密貨幣價格串流服務器...")
    subprocess.run([sys.executable, "./src/main.py"])


def run_enhanced_server():
    """
    運行增強版本的加密貨幣價格串流服務器。

    此函數會啟動位於 `./src/enhanced_main.py` 的增強服務器，該服務器可能包含更多功能或優化。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("🚀 正在啟動增強版加密貨幣價格串流服務器...")
    subprocess.run([sys.executable, "./src/enhanced_main.py"])


def test_influxdb():
    """
    測試與 InfluxDB 資料庫的連接。

    此函數會執行 `./src/influx-connector.py` 腳本，以驗證 InfluxDB 的連接配置是否正確。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("🔧 正在測試 InfluxDB 連接...")
    subprocess.run([sys.executable, "./src/influx-connector.py"])


def run_data_analyzer():
    """
    運行數據分析器。

    此函數會啟動位於 `./src/data_analyzer.py` 的數據分析腳本，用於處理和分析已收集的加密貨幣數據。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("📊 正在運行數據分析器...")
    subprocess.run([sys.executable, "./src/data_analyzer.py"])


def install_dependencies():
    """
    安裝項目所需的所有 Python 依賴包。

    此函數會使用 pip 從 `requirements.txt` 文件中安裝所有列出的依賴。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("📦 正在安裝項目依賴...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def check_environment():
    """
    檢查運行環境配置，特別是 `.env` 文件中的必要環境變數。

    此函數會檢查 `.env` 文件是否存在，並確保所有必要的環境變數（如 InfluxDB 和 Binance 相關變數）都已設置且非空。

    輸入參數:
        無

    輸出參數:
        bool: 如果所有必要的環境變數都已正確配置，則返回 True；否則返回 False。
    """
    logging.info("🔍 正在檢查環境配置...")

    required_env_vars = [
        'INFLUXDB_HOST',
        'INFLUXDB_TOKEN',
        'INFLUXDB_DATABASE',
        'BINANCE_SYMBOL',
        'BINANCE_INTERVAL'
    ]

    env_file = Path('.env')
    if not env_file.exists():
        logging.error("❌ .env 文件未找到。請根據 .env.example 創建一個。")
        return False

    # Load and check .env file
    missing_vars = []
    with open('.env', 'r') as f:
        env_content = f.read()
        for var in required_env_vars:
            if f"{var}=" not in env_content or f"{var}=" in env_content and not \
                    env_content.split(f"{var}=")[1].split('\n')[0].strip():
                missing_vars.append(var)

    if missing_vars:
        logging.error(f"❌ 缺少或空的環境變數: {', '.join(missing_vars)}")
        logging.error("請檢查您的 .env 文件並確保所有必要的變數都已設置。")
        return False

    logging.info("✅ 環境配置檢查通過")
    return True


def show_status():
    """
    顯示項目的當前狀態，包括重要文件狀態、環境配置和可用命令。

    此函數會列出關鍵文件的存在性，並調用 `check_environment` 函數來檢查環境變數，
    最後提供運行腳本的常用命令示例。

    輸入參數:
        無

    輸出參數:
        無
    """
    logging.info("📋 項目狀態檢查")
    logging.info("=" * 40)

    # Check files
    important_files = [
        '.env',
        'requirements.txt',
        'src/main.py',
        'src/enhanced_main.py',
        'src/crypto_provider.py',
        'src/enhanced_crypto_provider.py',
        'src/data_analyzer.py',
        'src/config.py'
    ]

    logging.info("📁 文件狀態:")
    for file_path in important_files:
        if Path(file_path).exists():
            logging.info(f"  ✅ {file_path}")
        else:
            logging.info(f"  ❌ {file_path} (缺失)")

    logging.info("\n🔧 環境狀態:")
    check_environment()

    logging.info("\n📚 可用命令:")
    logging.info("  python run.py --enhanced     # 運行增強版服務器")
    logging.info("  python run.py --basic        # 運行基本版服務器")
    logging.info("  python run.py --test-db      # 測試 InfluxDB 連接")
    logging.info("  python run.py --analyze      # 運行數據分析器")
    logging.info("  python run.py --install      # 安裝依賴包")


def main():
    """
    主函數，解析命令行參數並執行相應的操作。

    此函數使用 `argparse` 處理用戶提供的命令行參數，例如啟動不同版本的服務器、
    測試資料庫連接、運行數據分析器、安裝依賴或顯示項目狀態。
    在執行服務器或分析器之前，會先進行環境檢查。

    輸入參數:
        無 (通過命令行參數接收輸入)

    輸出參數:
        無
    """
    parser = argparse.ArgumentParser(
        description="Crypto Price Stream 運行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run.py --enhanced         # 運行增強版服務器
  python run.py --basic            # 運行基本版服務器
  python run.py --test-db          # 測試 InfluxDB 連接
  python run.py --analyze          # 運行數據分析器
  python run.py --install          # 安裝依賴包
  python run.py --status           # 檢查項目狀態
        """
    )

    parser.add_argument('--enhanced', action='store_true',
                        help='運行增強版服務器（推薦）')
    parser.add_argument('--basic', action='store_true',
                        help='運行基本版服務器')
    parser.add_argument('--test-db', action='store_true',
                        help='測試 InfluxDB 連接')
    parser.add_argument('--analyze', action='store_true',
                        help='運行數據分析器')
    parser.add_argument('--install', action='store_true',
                        help='安裝項目依賴')
    parser.add_argument('--status', action='store_true',
                        help='檢查項目狀態')

    args = parser.parse_args()

    # If no arguments provided, show status
    if not any(vars(args).values()):
        show_status()
        return

    # Pre-flight checks
    if args.enhanced or args.basic or args.analyze:
        if not check_environment():
            logging.error("\n❌ 環境檢查失敗。請在繼續之前修復上述問題。")
            return

    # Execute requested action
    try:
        if args.install:
            install_dependencies()
        elif args.test_db:
            test_influxdb()
        elif args.analyze:
            run_data_analyzer()
        elif args.enhanced:
            run_enhanced_server()
        elif args.basic:
            run_basic_server()
        elif args.status:
            show_status()

    except KeyboardInterrupt:
        logging.info("\n⚠️  用戶中斷操作")
    except Exception as e:
        logging.error(f"\n❌ 錯誤: {e}")


if __name__ == "__main__":
    logging.info("🎯 加密貨幣價格串流運行工具")
    logging.info("=" * 40)
    main()
