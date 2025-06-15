# 🚀 增強型加密貨幣價格串流服務器

一個強大的即時加密貨幣價格串流服務器，集成 InfluxDB 存儲、數據分析和監控功能，使用 FastAPI 和 WebSockets 建構。

---

[English](README.md) | 中文

---

## ✨ 主要功能

- **📈 即時價格串流**: 來自 Binance WebSocket 的即時加密貨幣價格數據。
- **💾 InfluxDB 整合**: 自動存儲價格數據以供歷史分析，並優化批次寫入。
- **🔄 WebSocket API**: 向連接的客戶端即時廣播價格數據。
- **🌐 RESTful 端點**: 簡易的訂閱管理、健康監控和數據檢索。
- **📊 數據分析工具**: 內建的數據分析和統計功能，提供市場洞察。
- **🖥️ Web 監控面板**: 即時監控和可視化界面，顯示系統和價格數據。
- **⚙️ 環境配置**: 使用 `.env` 文件的安全配置管理，並提供詳細說明。
- **🏗️ 模組化架構**: 清晰的關注點分離和專用提供者，以及明確的包結構。
- **📋 優雅降級**: 優雅處理可選依賴（Kafka、PostgreSQL），即使未安裝也能保持核心功能。
- **📈 性能監控**: 各組件的詳細統計和性能指標。
- **📦 包管理**: 利用 `setup.py` 進行正確的項目打包和依賴管理，通過 `pip install -e .` 安裝。
- **🔄 持久化訂閱**: 自動加載並訂閱數據庫中保存的符號（SQLite 或 PostgreSQL）。

## 🏗️ 項目架構

```
📁 Project Root
├── 📄 setup.py                                  # 項目打包和依賴管理
├── 📄 run.py                                    # 運行腳本 (推薦)
├── 📄 .env.example                              # 環境變數範例 (包含詳細註釋)
├── 📄 docker-compose-demo.yaml                  # 依賴服務的 Docker-compose 範例
├── 📄 README.md                                 # 項目說明文件 (英文)
├── 📄 README_zh-TW.md                           # 項目說明文件 (繁體中文)
├── 📁 src/
│   └── 📁 person_chart/                         # Python 包根目錄
│       ├── 📄 __init__.py                       # 使 person_chart 成為一個包
│       ├── 📄 colored_logging.py                # 彩色日誌設置
│       ├── 📄 config.py                         # 集中式環境變數配置管理
│       ├── 📄 data_models.py                    # 數據類 (PriceData, Stats, etc.)
│       ├── 📄 enhanced_main.py                  # 增強版 FastAPI 應用 (推薦)
│       ├── 📄 main.py                           # 基本版 FastAPI 應用
│       ├── 📁 analysis/                         # 數據分析子包
│       │   ├── 📄 __init__.py
│       │   └── 📄 data_analyzer.py              # 數據分析工具
│       ├── 📁 providers/                        # 數據提供者子包
│       │   ├── 📄 __init__.py
│       │   ├── 📄 abstract_data_provider.py     # 提供者的抽象基類
│       │   ├── 📄 crypto_provider.py            # 基本版價格提供者
│       │   └── 📄 enhanced_crypto_provider.py   # 增強版價格提供者
│       ├── 📁 services/                         # 外部服務管理子包
│       │   ├── 📄 __init__.py
│       │   ├── 📄 database_manager.py           # 管理訂閱持久化 (SQLite/PostgreSQL)
│       │   └── 📄 kafka_manager.py              # 管理 Kafka 連接
│       └── 📁 tools/                            # 命令行工具子包
│           ├── 📄 __init__.py
│           ├── 📄 influx-connector.py           # InfluxDB 連接測試工具
│           └── 📄 time_unity.py                 # 時間單位轉換工具
└── 📁 static/                                   # Web 儀表板的靜態文件
    └── 📄 index.html                            # Web 監控儀表板 HTML
```

### 🔧 核心組件

1. **`EnhancedCryptoPriceProvider`**: 處理 Binance WebSocket 連接和價格數據處理，支持緩存、價格變化計算和統計。它還提供歷史數據查詢功能。
2. **`EnhancedInfluxDBManager`**: 管理 InfluxDB 連接和優化批次數據寫入，支持後台處理以實現高效數據攝取。
3. **`EnhancedConnectionManager` (在 `enhanced_main.py` 中)**: 管理 WebSocket 客戶端連接，廣播即時數據，並協調數據提供者。增強版集成了
   Kafka 用於消息隊列。
4. **`CryptoDataAnalyzer`**: 提供歷史數據分析、市場摘要、交易統計、價格警報和來自 InfluxDB 的交易量分析。
5. **`Config`**: 集中式環境變數配置管理，確保安全靈活的部署。
6. **`SubscriptionRepository`**: 管理訂閱符號在數據庫（SQLite 或 PostgreSQL）中的持久化。
7. **`KafkaManager`**: 處理 Kafka 生產者和消費者創建，實現數據分發的強大消息隊列。

### 📊 版本對比

| 功能模組       | 基本版 (`main.py`)         | 增強版 (`enhanced_main.py`)  | 備註                           |
|------------|-------------------------|---------------------------|------------------------------|
| 數據獲取       | ✅ 增強版提供者                | ✅ 增強版提供者                  | 兩個版本使用相同的加強版數據提供者。           |
| 持久化訂閱      | ✅ (SQLite / PostgreSQL) | ✅ (SQLite / PostgreSQL)   | 兩個版本都支持加載/保存訂閱。              |
| 數據儲存       | ✅ InfluxDB (基礎+聚合)      | ✅ InfluxDB (基礎+聚合)        | 兩個版本都會儲存基礎和聚合後的 K 線數據。       |
| 配置管理       | ✅ `config.py`           | ✅ `config.py`             | 兩者共用，但增強版會使用更多配置項。           |
| 即時數據分發     | ✅ 基礎 WebSocket 廣播       | ✅ WebSocket 廣播 & Kafka    | 增強版增加了可選的 Kafka 以實現更可靠的消息隊列。 |
| API 服務     | ✅ (極簡)                  | ✅ (豐富)                    | 增強版增加了歷史數據、分析、統計等豐富的 API。    |
| 前端界面       | ❌                       | ✅ (Web 監控儀表板)             | 這是增強版最顯著的區別。                 |
| 歷史數據查詢 API | ❌                       | ✅ (為圖表提供 API)             | 僅增強版提供查詢歷史數據的 API。           |
| 數據分析 API   | ❌                       | ✅ (`data_analyzer.py` 整合) | 僅增強版提供分析報告的 API。             |
| Kafka 整合   | ❌                       | ✅ (可選)                    | 作為高級功能，只在增強版中提供。             |

## 🚀 快速開始

### 1. 克隆倉庫

```bash
git clone https://github.com/tommot20077/tradingview-chart.git 
cd person-chart
```

### 2. 配置環境

複製環境變數範例文件並配置設定：

```bash
cp .env.example .env
```

編輯 `.env` 文件，填入你的實際配置（請參考 `.env.example` 中的詳細註釋）。

### 3. 安裝項目依賴

以可編輯模式安裝項目。這確保所有本地模塊都能正確識別並安裝依賴。

```bash
python run.py --install
```

### 4. 測試 InfluxDB 連接

在運行主應用程式之前，測試你的 InfluxDB 連接：

```bash
python run.py --test-db
```

這將會：

- 測試與 InfluxDB 實例的連接。
- 寫入樣本數據。
- 查詢並顯示測試數據。

### 5. 運行服務器

**推薦方式 - 使用運行腳本（通過控制台腳本使用 `uvicorn`）：**

```bash
# 運行增強版服務器 (推薦，包含 Web 儀表板和高級功能)
python run.py --enhanced

# 或運行基本版服務器 (最小功能)
python run.py --basic

# 檢查項目狀態和可用命令
python run.py --status
```

### 6. 訪問 Web 監控儀表板 (僅限增強版)

運行增強版服務器 (`python run.py --enhanced`) 後，在瀏覽器中訪問：

```
http://localhost:8000
```

你將看到包含以下內容的即時監控面板：

- 📊 系統統計信息
- 💰 即時價格顯示
- 🔄 連接狀態
- 📈 性能指標

### 7. 運行數據分析

```bash
python run.py --analyze
```

這將執行 `data_analyzer.py` 腳本，該腳本從 InfluxDB 獲取可用符號並為第一個可用符號生成綜合分析報告。

## API 端點

### REST 端點

- `GET /` - API 資訊和狀態（基本版）/ Web 監控儀表板（增強版）
- `GET /health` - 健康檢查和系統狀態
- `GET /config` - 當前配置（不包括敏感數據）
- `GET /stats` - 詳細系統和加密貨幣提供者統計（僅限增強版）
- `GET /prices` - 獲取所有已緩存符號的最新價格（僅限增強版）
- `POST /symbol/{symbol}/subscribe` - 訂閱交易對的價格串流
- `POST /symbol/{symbol}/unsubscribe` - 取消訂閱交易對的價格串流
- `GET /historical/{symbol}` - 獲取符號的歷史 K 線數據（僅限增強版）
- `GET /symbols` - 獲取當前已訂閱和已緩存符號列表（僅限增強版）

### WebSocket 端點

- `ws://localhost:8000/ws/price` - 即時價格串流

## 使用範例

### 訂閱額外符號

```bash
# 訂閱以太坊
curl -X POST "http://localhost:8000/symbol/ethusdt/subscribe"

# 訂閱狗狗幣
curl -X POST "http://localhost:8000/symbol/dogeusdt/subscribe"
```

### 檢查系統健康狀況

```bash
curl http://localhost:8000/health
```

回應（增強版範例）：

```json
{
  "status": "healthy",
  "timestamp": "2025-06-14T12:00:00.000000+00:00",
  "crypto_provider": "running",
  "active_websocket_connections": 2,
  "connection_stats": {
    "total_connections": 5,
    "messages_sent": 120,
    "failed_sends": 0
  },
  "subscribed_symbols": [
    "BNBUSDT@kline_1m",
    "ETHUSDT@kline_1m"
  ],
  "provider_stats": {
    "messages_received": 150,
    "messages_processed": 145,
    "messages_failed": 5,
    "kafka_messages_sent": 145,
    "start_time": "2025-06-14T11:00:00.000000+00:00",
    "uptime_seconds": 3600.0,
    "subscribed_symbols": [
      "bnbusdt@kline_1m",
      "ethusdt@kline_1m"
    ],
    "cached_symbols": [
      "BNBUSDT",
      "ETHUSDT"
    ],
    "influxdb_stats": {
      "total_writes": 145,
      "successful_writes": 140,
      "failed_writes": 5,
      "retry_count": 2,
      "last_write_time": "2025-06-14T11:59:50.000000+00:00",
      "queue_size": 0
    }
  }
}
```

### WebSocket 客戶端範例 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/price');

ws.onopen = function (event) {
    console.log('已連接到價格串流');
    // 你可以從客戶端發送訂閱命令 (僅限增強版)
    // ws.send('subscribe:ETHUSDT');
};

ws.onmessage = function (event) {
    const priceData = JSON.parse(event.data);
    console.log('價格更新:', priceData);
};

ws.onclose = function (event) {
    console.log('已從價格串流斷開連接');
};
```

## 數據存儲

價格數據會自動存儲在 InfluxDB 中，其架構如下：

**測量 (Measurement)**: `crypto_price`

**標籤 (Tags)**:

- `symbol`: 加密貨幣符號 (例如 "BTCUSDT")

**字段 (Fields)**:

- `price`: 當前價格 (收盤價)
- `open`: 開盤價
- `high`: 區間內最高價
- `low`: 區間內最低價
- `close`: 收盤價
- `volume`: 交易量
- `price_change` (可選，增強版): 相對於前一個數據點的價格變化。
- `price_change_percent` (可選，增強版): 相對於前一個數據點的價格變化百分比。
- `trade_count` (可選，增強版): K 線期間的交易數量。

**時間戳 (Timestamp)**: 價格數據時間戳

### 查詢數據

你可以使用 InfluxDB 的類 SQL 語法查詢歷史數據：

```sql
SELECT *
FROM crypto_price
WHERE symbol = 'BTCUSDT'
  AND time >= now() - interval '1 hour'
ORDER BY time DESC
LIMIT 100
```

## 開發

### 運行測試

使用提供的 HTTP 測試文件 (`src/test_main.http`) 與你喜歡的 REST 客戶端（例如，VS Code REST Client 擴展、Postman、Insomnia）。

### 日誌記錄

應用程式使用結構化日誌記錄，具有以下級別：

- `INFO`: 一般應用程式流程和成功操作。
- `WARNING`: 非關鍵問題（例如，WebSocket 廣播失敗，Kafka 未安裝）。
- `ERROR`: 需要注意的關鍵錯誤（例如，InfluxDB 連接失敗，配置無效）。

日誌格式：

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 添加新的提供者

要添加對其他加密貨幣交易所的支持：

1. 創建一個類似 `CryptoPriceProviderRealtime` 或 `EnhancedCryptoPriceProviderRealtime` 的新提供者類。
2. 實現 `AbstractRealtimeDataProvider`（並可選地 `AbstractHistoricalDataProvider`）接口以保持一致性。
3. 更新 `config.py` 以支持新的提供者特定設置。
4. 修改 `ConnectionManager` 或 `EnhancedConnectionManager` 以集成和管理新的數據源。

## 安全考量

- **環境變數**: 敏感數據（API 令牌、數據庫憑據）存儲在 `.env` 文件中，並從版本控制中排除（`.gitignore`）。
- **令牌暴露**: `/config` 端點明確將敏感令牌從其回應中排除。
- **輸入驗證**: 符號名稱和其他輸入在適當位置進行驗證，以防止常見漏洞。
- **CORS**: 默認配置為允許所有來源用於開發；**對於生產環境，請將 `allow_origins` 限制為特定域名。**

## 故障排除

### 常見問題

1. **InfluxDB 連接失敗**
    - 檢查你的 `.env` 文件中的 `INFLUXDB_HOST`、`INFLUXDB_TOKEN` 和 `INFLUXDB_DATABASE` 設置。
    - 確保 InfluxDB 正在運行且可訪問（例如，如果使用 `docker-compose`，請檢查 Docker 容器狀態）。
    - 運行 `python run.py --test-db` 測試連接。

2. **Binance WebSocket 連接問題**
    - 檢查你的互聯網連接。
    - 驗證符號名稱是否有效（例如，`btcusdt`、`ethusdt` 使用小寫）。
    - 檢查 Binance API 狀態頁面是否有任何正在進行的問題。

3. **WebSocket 客戶端未接收到數據**
    - 驗證 WebSocket 端點是否正確：`ws://localhost:8000/ws/price`。
    - 檢查服務器日誌以查找連接問題或數據處理/廣播期間的錯誤。
    - 確保加密貨幣提供者正在運行（檢查 `/health` 端點）。

4. **Kafka 或 PostgreSQL 錯誤**
    - 確保你已安裝可選依賴：Kafka 為 `pip install -e .[kafka]`，PostgreSQL 為 `pip install -e .[postgresql]`。
    - 驗證 Kafka 或 PostgreSQL 服務正在運行且可訪問（檢查 `docker-compose-demo.yaml` 中的默認端口）。
    - 檢查 Kafka 代理日誌或 PostgreSQL 數據庫日誌以獲取特定錯誤消息。

### 調試模式

要啟用調試日誌記錄，請修改 `src/main.py` 或 `src/enhanced_main.py` 中的日誌配置：

```python
logging.basicConfig(level=logging.DEBUG)
```

## 性能調優

### InfluxDB 寫入優化

根據你的需求調整 `EnhancedInfluxDBManager`（在 `src/enhanced_crypto_provider.py` 中）中的寫入選項：

```python
write_options = WriteOptions(
    batch_size=500,  # 增加以提高吞吐量 (enhanced_main.py 中默認為 200)
    flush_interval=10_000,  # 減少以降低延遲 (默認為 5_000)
    max_retries=5  # 根據網絡可靠性調整
)
```

### WebSocket 連接限制

服務器可以處理多個 WebSocket 連接。監控性能並根據需要調整服務器資源（CPU、RAM）。

## 許可證

此項目僅用於教育和研究目的。

## 貢獻

1. Fork 倉庫。
2. 創建一個功能分支（`git checkout -b feature/YourFeature`）。
3. 進行你的更改。
4. 如果適用，添加測試。
5. 確保所有文檔字符串和註釋都使用繁體中文以保持一致性。
6. 提交拉取請求。

對於重大更改，請先開一個 issue 討論擬議的更改。
