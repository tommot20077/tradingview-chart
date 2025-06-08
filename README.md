# 🚀 Enhanced Crypto Price Stream Server

一個強大的即時加密貨幣價格串流服務器，集成 InfluxDB 存儲、數據分析和監控功能，使用 FastAPI 和 WebSockets 建構。

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

| 功能 | 基本版 | 增強版 |
|------|--------|--------|
| WebSocket 串流 | ✅ | ✅ |
| InfluxDB 存儲 | ✅ | ✅ |
| 批次寫入優化 | ❌ | ✅ |
| 價格變化計算 | ❌ | ✅ |
| 統計監控 | ❌ | ✅ |
| Web 控制面板 | ❌ | ✅ |
| 數據分析工具 | ❌ | ✅ |
| 性能緩存 | ❌ | ✅ |

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

## API Endpoints

### REST Endpoints

- `GET /` - API information and status
- `GET /health` - Health check and system status
- `GET /config` - Current configuration (excluding sensitive data)
- `POST /symbol/{symbol}/subscribe` - Subscribe to a symbol's price stream
- `POST /symbol/{symbol}/unsubscribe` - Unsubscribe from a symbol's price stream

### WebSocket Endpoint

- `ws://localhost:8000/ws/price` - Real-time price streaming

## Usage Examples

### Subscribe to Additional Symbols

```bash
# Subscribe to Ethereum
curl -X POST "http://localhost:8000/symbol/ethusdt/subscribe?interval=1m"

# Subscribe to Dogecoin
curl -X POST "http://localhost:8000/symbol/dogeusdt/subscribe?interval=5m"
```

### Check System Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "crypto_provider": "running",
  "active_websocket_connections": 2,
  "subscribed_symbols": ["bnbusdt@kline_1m", "ethusdt@kline_1m"]
}
```

### WebSocket Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/price');

ws.onopen = function(event) {
    console.log('Connected to price stream');
};

ws.onmessage = function(event) {
    const priceData = JSON.parse(event.data);
    console.log('Price update:', priceData);
};

ws.onclose = function(event) {
    console.log('Disconnected from price stream');
};
```

## Data Storage

Price data is automatically stored in InfluxDB with the following schema:

**Measurement**: `crypto_price`

**Tags**:
- `symbol`: Cryptocurrency symbol (e.g., "BTCUSDT")

**Fields**:
- `price`: Current price (close price)
- `open`: Opening price
- `high`: Highest price in the interval
- `low`: Lowest price in the interval
- `close`: Closing price
- `volume`: Trading volume

**Timestamp**: Price data timestamp

### Querying Data

You can query historical data using InfluxDB's SQL-like syntax:

```sql
SELECT *
FROM crypto_price
WHERE symbol = 'BTCUSDT'
  AND time >= now() - interval '1 hour'
ORDER BY time DESC
LIMIT 100
```

## Development

### Running Tests

Use the provided HTTP test file with your favorite REST client:

```bash
# Using the test_main.http file with VS Code REST Client extension
# or import into Postman/Insomnia
```

### Logging

The application uses structured logging with the following levels:
- `INFO`: General application flow and successful operations
- `WARNING`: Non-critical issues (e.g., failed WebSocket broadcasts)
- `ERROR`: Critical errors that need attention

Log format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Adding New Providers

To add support for additional cryptocurrency exchanges:

1. Create a new provider class similar to `CryptoPriceProvider`
2. Implement the same interface for consistency
3. Update the configuration to support multiple providers
4. Modify the connection manager to handle multiple data sources

## Security Considerations

- **Environment Variables**: Sensitive data (tokens, hosts) are stored in `.env` files
- **Git Ignore**: The `.env` file is excluded from version control
- **Token Exposure**: The `/config` endpoint excludes sensitive tokens from the response
- **Input Validation**: Symbol names are validated before subscription

## Troubleshooting

### Common Issues

1. **InfluxDB Connection Failed**
   - Check your `INFLUXDB_HOST`, `INFLUXDB_TOKEN`, and `INFLUXDB_DATABASE` settings
   - Ensure InfluxDB is running and accessible
   - Run `python influx-connector.py` to test connectivity

2. **Binance WebSocket Connection Issues**
   - Check internet connectivity
   - Verify symbol names are valid (use lowercase)
   - Check Binance API status

3. **WebSocket Clients Not Receiving Data**
   - Verify the WebSocket endpoint is correct: `ws://localhost:8000/ws/price`
   - Check the server logs for connection issues
   - Ensure the crypto provider is running (check `/health` endpoint)

### Debug Mode

To enable debug logging, modify the logging configuration in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tuning

### InfluxDB Write Optimization

Adjust write options in `CryptoPriceProvider` for your needs:

```python
write_options = WriteOptions(
    batch_size=500,      # Increase for higher throughput
    flush_interval=10_000,  # Reduce for lower latency
    max_retries=5        # Adjust based on network reliability
)
```

### WebSocket Connection Limits

The server can handle multiple WebSocket connections. Monitor performance and adjust server resources as needed.

## License

This project is for educational and research purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

For major changes, please open an issue first to discuss the proposed changes.
