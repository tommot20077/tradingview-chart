# 🚀 Enhanced Crypto Price Stream Server

A powerful real-time cryptocurrency price streaming server integrating InfluxDB storage, data analysis, and monitoring
capabilities, built with FastAPI and WebSockets.

---

English | [中文](README_zh-TW.md)

---

## ✨ Key Features

- **📈 Real-time Price Streaming**: Live cryptocurrency price data from Binance WebSocket
- **💾 InfluxDB Integration**: Automatic storage of price data for historical analysis
- **🔄 WebSocket API**: Real-time broadcasting of price data to connected clients
- **🌐 RESTful Endpoints**: Easy subscription management and health monitoring
- **📊 Data Analysis Tools**: Built-in data analysis and statistical functions
- **🖥️ Web Monitoring Dashboard**: Real-time monitoring and visualization interface
- **⚙️ Environment Configuration**: Secure configuration management using `.env` files
- **🏗️ Modular Architecture**: Clear separation of concerns with dedicated providers
- **📋 Batch Processing**: Optimized InfluxDB batch writing performance
- **📈 Performance Monitoring**: Detailed statistics and performance metrics

## 🏗️ Project Architecture

```
📁 Project Root
├── 📄 run.py                      # Unified run script (recommended)
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env                        # Environment variables (not in git)
├── 📄 .env.example               # Example environment variables
├── 📄 README.md                  # Project documentation
└── 📁 src/                       # Source code directory
    ├── 📄 main.py                # Basic FastAPI application
    ├── 📄 enhanced_main.py       # Enhanced FastAPI application (recommended)
    ├── 📄 crypto_price_provider.py    # Basic price provider
    ├── 📄 enhanced_crypto_provider.py # Enhanced price provider
    ├── 📄 data_analyzer.py       # Data analysis tools
    ├── 📄 config.py              # Configuration management
    ├── 📄 influx-connector.py    # InfluxDB connection test utility
    └── 📄 test_main.http         # API endpoint tests
```

### 🔧 Core Components

1. **Enhanced CryptoPriceProvider**: Handles Binance WebSocket connections and price data processing, supports caching
   and statistics.
2. **Enhanced InfluxDBManager**: Manages InfluxDB connections and batch data writing, supports background processing.
3. **ConnectionManager**: Manages WebSocket client connections and broadcasting.
4. **DataAnalyzer**: Provides historical data analysis and statistical functions.
5. **Config**: Centralized environment variable configuration management.

### 📊 Version Comparison

| Feature                  | Basic Version | Enhanced Version |
|--------------------------|---------------|------------------|
| WebSocket Streaming      | ✅             | ✅                |
| InfluxDB Storage         | ✅             | ✅                |
| Batch Write Optimization | ❌             | ✅                |
| Price Change Calculation | ❌             | ✅                |
| Statistical Monitoring   | ❌             | ✅                |
| Web Control Panel        | ❌             | ✅                |
| Data Analysis Tools      | ❌             | ✅                |
| Performance Caching      | ❌             | ✅                |

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using the run script (recommended)
python run.py --install

# Or manual installation
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment variables file and configure settings:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual configuration:

```env
# InfluxDB Configuration
INFLUXDB_HOST=http://your-influxdb-host:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_DATABASE=your-database-name

# Binance Configuration
BINANCE_SYMBOL=btcusdt
BINANCE_INTERVAL=1m

# Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
```

### 3. Test InfluxDB Connection

Before running the main application, test your InfluxDB connection:

```bash
# Using the run script
python run.py --test-db

# Or run directly
cd src && python influx-connector.py
```

This will:

- Test connection to your InfluxDB instance
- Write sample data
- Query and display test data

### 4. Run Server

**Recommended way - using the run script:**

```bash
# Run enhanced server (recommended)
python run.py --enhanced

# Or run basic server
python run.py --basic

# Check project status
python run.py --status
```

**Traditional way:**

```bash
# Enhanced version
cd src && python enhanced_main.py

# Basic version
cd src && python main.py

# Or using uvicorn
uvicorn src.enhanced_main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access Web Monitoring Dashboard

After running the enhanced server, visit in your browser:

```
http://localhost:8000
```

You will see a real-time monitoring dashboard with:

- 📊 System statistics
- 💰 Live price display
- 🔄 Connection status
- 📈 Performance metrics

### 6. Run Data Analysis

```bash
# Using the run script
python run.py --analyze

# Or run directly
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
  "subscribed_symbols": [
    "bnbusdt@kline_1m",
    "ethusdt@kline_1m"
  ]
}
```

### WebSocket Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/price');

ws.onopen = function (event) {
    console.log('Connected to price stream');
};

ws.onmessage = function (event) {
    const priceData = JSON.parse(event.data);
    console.log('Price update:', priceData);
};

ws.onclose = function (event) {
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
    batch_size=500,  # Increase for higher throughput
    flush_interval=10_000,  # Reduce for lower latency
    max_retries=5  # Adjust based on network reliability
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
