# 🚀 增強型加密貨幣價格串流服務器

一個強大的即時加密貨幣價格串流服務器，集成 InfluxDB 存儲、數據分析和監控功能，使用 FastAPI 和 WebSockets 建構。

[View English Version](../../README.md)

---

## ✨ 主要功能

- **📈 即時價格串流**: 來自 Binance WebSocket 的即時加密貨幣價格數據
- **💾 InfluxDB 整合**: 自動存儲價格數據以供歷史分析
- **🔄 WebSocket API**: 向連接的客戶端即時廣播價格數據
- **🌐 RESTful 端點**: 簡易的訂閱管理和健康監控
- **📊 數據分析工具**: 內建的數據分析和統計功能
- **🖥️ Web 監控面板**: 即時監控和可視化界面
- **⚙️ 環境配置**: 使用 `.env` 文件的安全配置管理
- **🏗️ 模組化架構**: 清晰的關注點分離和專用提供者
- **📋 批次處理**: 優化的 InfluxDB 批次寫入性能
- **📈 性能監控**: 詳細的統計和性能指標

## 🏗️ 項目架構

```
📁 項目根目錄
├── 📄 run.py                      # 統一運行腳本 (推薦使用)
├── 📄 requirements.txt            # Python 依賴包
├── 📄 .env                        # 環境變數 (不在 git 中)
├── 📄 .env.example               # 環境變數範例
├── 📄 README.md                  # 項目說明文件
└── 📁 src/                       # 源代碼目錄
    ├── 📄 main.py                # 基本版 FastAPI 應用
    ├── 📄 enhanced_main.py       # 增強版 FastAPI 應用 (推薦)
    ├── 📄 crypto_price_provider.py    # 基本版價格提供者
    ├── 📄 enhanced_crypto_provider.py # 增強版價格提供者
    ├── 📄 data_analyzer.py       # 數據分析工具
    ├── 📄 config.py              # 配置管理
    ├── 📄 influx-connector.py    # InfluxDB 連接測試工具
    └── 📄 test_main.http         # API 端點測試
```

### 🔧 核心組件

1. **增強版 CryptoPriceProvider**: 處理 Binance WebSocket 連接和價格數據處理，支持緩存和統計
2. **增強版 InfluxDBManager**: 管理 InfluxDB 連接和批次數據寫入，支持背景處理
3. **ConnectionManager**: 管理 WebSocket 客戶端連接和廣播
4. **DataAnalyzer**: 提供歷史數據分析和統計功能
5. **Config**: 集中式環境變數配置管理

### 📊 版本對比

| 功能           | 基本版 | 增強版 |
|--------------|-----|-----|
| WebSocket 串流 | ✅   | ✅   |
| InfluxDB 存儲  | ✅   | ✅   |
| 批次寫入優化       | ❌   | ✅   |
| 價格變化計算       | ❌   | ✅   |
| 統計監控         | ❌   | ✅   |
| Web 控制面板     | ❌   | ✅   |
| 數據分析工具       | ❌   | ✅   |
| 性能緩存         | ❌   | ✅   |

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 使用運行腳本 (推薦)
python run.py --install

# 或手動安裝
pip install -r requirements.txt
```

### 2. 配置環境

複製環境變數範例文件並配置設定：

```bash
cp .env.example .env
```

編輯 `.env` 文件，填入你的實際配置：

```env
# InfluxDB 配置
INFLUXDB_HOST=http://your-influxdb-host:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_DATABASE=your-database-name

# Binance 配置
BINANCE_SYMBOL=btcusdt
BINANCE_INTERVAL=1m

# 服務器配置
API_HOST=127.0.0.1
API_PORT=8000
```

### 3. 測試 InfluxDB 連接

在運行主應用程式之前，測試你的 InfluxDB 連接：

```bash
# 使用運行腳本
python run.py --test-db

# 或直接運行
cd src && python influx-connector.py
```

這將會：

- 測試與 InfluxDB 實例的連接
- 寫入樣本數據
- 查詢並顯示測試數據

### 4. 運行服務器

**推薦方式 - 使用運行腳本：**

```bash
# 運行增強版服務器 (推薦)
python run.py --enhanced

# 或運行基本版服務器
python run.py --basic

# 檢查項目狀態
python run.py --status
```

**傳統方式：**

```bash
# 增強版
cd src && python enhanced_main.py

# 基本版
cd src && python main.py

# 或使用 uvicorn
uvicorn src.enhanced_main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. 訪問 Web 控制面板

運行增強版服務器後，在瀏覽器中訪問：

```
http://localhost:8000
```

你將看到包含以下內容的即時監控面板：

- 📊 系統統計信息
- 💰 即時價格顯示
- 🔄 連接狀態
- 📈 性能指標

### 6. 運行數據分析

```bash
# 使用運行腳本
python run.py --analyze

# 或直接運行
cd src && python data_analyzer.py
```

## API 端點

### REST 端點

- `GET /` - API 資訊和狀態
- `GET /health` - 健康檢查和系統狀態
- `GET /config` - 當前配置 (不包括敏感數據)
- `POST /symbol/{symbol}/subscribe` - 訂閱交易對的價格串流
- `POST /symbol/{symbol}/unsubscribe` - 取消訂閱交易對的價格串流

### WebSocket 端點

- `ws://localhost:8000/ws/price` - 即時價格串流

## 使用範例

### 訂閱額外符號

```bash
# 訂閱以太坊
curl -X POST "http://localhost:8000/symbol/ethusdt/subscribe?interval=1m"

# 訂閱狗狗幣
curl -X POST "http://localhost:8000/symbol/dogeusdt/subscribe?interval=5m"
```

### 檢查系統健康狀況

```bash
curl http://localhost:8000/health
```

回應:

```json
{
  "status": "healthy",
  "crypto_provider": "running",
  "active_websocket_connections": 2,
  "subscribed_symbols": [
    "bnbusdt@kline_1m",
    "ethusdt@kline_1m"
  ]
}
```

### WebSocket 客戶端範例 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/price');

ws.onopen = function (event) {
    console.log('已連接到價格串流');
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

使用提供的 HTTP 測試文件與你喜歡的 REST 客戶端：

```bash
# 使用 VS Code REST Client 擴展的 test_main.http 文件
# 或導入到 Postman/Insomnia
```

### 日誌記錄

應用程式使用結構化日誌記錄，具有以下級別：

- `INFO`: 一般應用程式流程和成功操作
- `WARNING`: 非關鍵問題 (例如，WebSocket 廣播失敗)
- `ERROR`: 需要注意的關鍵錯誤

日誌格式：

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 添加新的提供者

要添加對其他加密貨幣交易所的支持：

1. 創建一個類似 `CryptoPriceProvider` 的新提供者類
2. 實現相同的接口以保持一致性
3. 更新配置以支持多個提供者
4. 修改連接管理器以處理多個數據源

## 安全考量

- **環境變數**: 敏感數據 (令牌、主機) 存儲在 `.env` 文件中
- **Git 忽略**: `.env` 文件被排除在版本控制之外
- **令牌暴露**: `/config` 端點將敏感令牌從回應中排除
- **輸入驗證**: 符號名稱在訂閱前進行驗證

## 故障排除

### 常見問題

1. **InfluxDB 連接失敗**
    - 檢查你的 `INFLUXDB_HOST`、`INFLUXDB_TOKEN` 和 `INFLUXDB_DATABASE` 設定
    - 確保 InfluxDB 正在運行且可訪問
    - 運行 `python influx-connector.py` 測試連接

2. **Binance WebSocket 連接問題**
    - 檢查網路連接
    - 驗證符號名稱是否有效 (使用小寫)
    - 檢查 Binance API 狀態

3. **WebSocket 客戶端未接收到數據**
    - 驗證 WebSocket 端點是否正確：`ws://localhost:8000/ws/price`
    - 檢查服務器日誌以查找連接問題
    - 確保加密貨幣提供者正在運行 (檢查 `/health` 端點)

### 調試模式

要啟用調試日誌記錄，請修改 `main.py` 中的日誌配置：

```python
logging.basicConfig(level=logging.DEBUG)
```

## 性能調優

### InfluxDB 寫入優化

根據你的需求調整 `CryptoPriceProvider` 中的寫入選項：

```python
write_options = WriteOptions(
    batch_size=500,  # 增加以提高吞吐量
    flush_interval=10_000,  # 減少以降低延遲
    max_retries=5  # 根據網路可靠性調整
)
```

### WebSocket 連接限制

服務器可以處理多個 WebSocket 連接。監控性能並根據需要調整服務器資源。

## 許可證

此項目僅用於教育和研究目的。

## 貢獻

1. Fork 倉庫
2. 創建一個功能分支
3. 進行你的更改
4. 如果適用，添加測試
5. 提交拉取請求

對於重大更改，請先開一個 issue 討論擬議的更改。


