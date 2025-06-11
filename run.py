#!/usr/bin/env python3
"""
Crypto Price Stream 運行腳本
提供多種運行選項和工具
"""

import sys
import argparse
import subprocess
import os
from pathlib import Path


def run_basic_server():
    """運行基本版本的服務器"""
    print("🚀 Starting Basic Crypto Price Stream Server...")
    subprocess.run([sys.executable, "./src/main.py"])


def run_enhanced_server():
    """運行增強版本的服務器"""
    print("🚀 Starting Enhanced Crypto Price Stream Server...")
    subprocess.run([sys.executable, "./src/enhanced_main.py"])


def test_influxdb():
    """測試 InfluxDB 連接"""
    print("🔧 Testing InfluxDB Connection...")
    subprocess.run([sys.executable, "./src/influx-connector.py"])


def run_data_analyzer():
    """運行數據分析器"""
    print("📊 Running Data Analyzer...")
    os.chdir("")
    subprocess.run([sys.executable, "data_analyzer.py"])


def install_dependencies():
    """安裝項目依賴"""
    print("📦 Installing project dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def check_environment():
    """檢查環境配置"""
    print("🔍 Checking environment configuration...")

    required_env_vars = [
        'INFLUXDB_HOST',
        'INFLUXDB_TOKEN',
        'INFLUXDB_DATABASE',
        'BINANCE_SYMBOL',
        'BINANCE_INTERVAL'
    ]

    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found. Please create one based on .env.example")
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
        print(f"❌ Missing or empty environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all required variables are set.")
        return False

    print("✅ Environment configuration looks good!")
    return True


def show_status():
    """顯示項目狀態"""
    print("📋 Project Status Check")
    print("=" * 40)

    # Check files
    important_files = [
        '.env',
        'requirements.txt',
        'src/main.py',
        'src/enhanced_main.py',
        'src/crypto_price_provider.py',
        'src/enhanced_crypto_provider.py',
        'src/data_analyzer.py',
        'src/config.py'
    ]

    print("📁 File Status:")
    for file_path in important_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (missing)")

    print("\n🔧 Environment Status:")
    check_environment()

    print("\n📚 Available Commands:")
    print("  python run.py --enhanced     # Run enhanced server")
    print("  python run.py --basic        # Run basic server")
    print("  python run.py --test-db      # Test InfluxDB connection")
    print("  python run.py --analyze      # Run data analyzer")
    print("  python run.py --install      # Install dependencies")


def main():
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
            print("\n❌ Environment check failed. Please fix the issues above before proceeding.")
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
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("🎯 Crypto Price Stream 運行工具")
    print("=" * 40)
    main()
