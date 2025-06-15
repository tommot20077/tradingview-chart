# 🚀 Enhanced Crypto Price Stream Server

A powerful real-time cryptocurrency price streaming server integrating InfluxDB storage, data analysis, and monitoring
capabilities, built with FastAPI and WebSockets.

---

English | [中文](README_zh-TW.md)

---

## ✨ Key Features

- **📈 Real-time Price Streaming**: Live cryptocurrency price data from Binance WebSocket.
- **💾 InfluxDB Integration**: Automatic storage of price data for historical analysis with optimized batch writing.
- **🔄 WebSocket API**: Real-time broadcasting of price data to connected clients.
- **🌐 RESTful Endpoints**: Easy subscription management, health monitoring, and data retrieval.
- **📊 Data Analysis Tools**: Built-in data analysis and statistical functions for market insights.
- **🖥️ Web Monitoring Dashboard**: Real-time monitoring and visualization interface for system and price data.
- **⚙️ Environment Configuration**: Secure configuration management using `.env` files with detailed explanations.
- **🏗️ Modular Architecture**: Clear separation of concerns with dedicated providers and a well-defined package
  structure.
- **📋 Graceful Degradation**: Handles optional dependencies (Kafka, PostgreSQL) gracefully, allowing core functionality
  even if not installed.
- **📈 Performance Monitoring**: Detailed statistics and performance metrics for various components.
- **📦 Package Management**: Utilizes `setup.py` for proper project packaging and dependency management
  via `pip install -e .`.
- **🔄 Persistent Subscriptions**: Automatically loads and subscribes to symbols saved in a database (SQLite or
  PostgreSQL).

## 🏗️ Project Architecture

```
📁 Project Root
├── 📄 setup.py                                  # Project packaging and dependency management
├── 📄 run.py                                    # Run script (recommended)
├── 📄 .env.example                              # Example environment variables with detailed comments
├── 📄 docker-compose-demo.yaml                  # Docker-compose for dependency services
├── 📄 README.md                                 # Project documentation (English)
├── 📄 README_zh-TW.md                           # Project documentation (Traditional Chinese)
├── 📁 src/
│   └── 📁 person_chart/                         # Python package root directory
│       ├── 📄 __init__.py                       # Makes person_chart a package
│       ├── 📄 colored_logging.py                # Colored logging setup
│       ├── 📄 config.py                         # Centralized environment variable configuration
│       ├── 📄 data_models.py                    # Data classes (PriceData, Stats, etc.)
│       ├── 📄 enhanced_main.py                  # Enhanced FastAPI application (recommended)
│       ├── 📄 main.py                           # Basic FastAPI application
│       ├── 📁 analysis/                         # Data analysis subpackage
│       │   ├── 📄 __init__.py
│       │   └── 📄 data_analyzer.py              # Data analysis tools
│       ├── 📁 providers/                        # Data providers subpackage
│       │   ├── 📄 __init__.py
│       │   ├── 📄 abstract_data_provider.py     # Abstract base class for providers
│       │   ├── 📄 crypto_provider.py            # Basic price provider
│       │   └── 📄 enhanced_crypto_provider.py   # Enhanced price provider
│       ├── 📁 services/                         # External service management subpackage
│       │   ├── 📄 __init__.py
│       │   ├── 📄 database_manager.py           # Manages subscription persistence (SQLite/PostgreSQL)
│       │   └── 📄 kafka_manager.py              # Manages Kafka connections
│       └── 📁 tools/                            # Command line tools subpackage
│           ├── 📄 __init__.py
│           ├── 📄 influx-connector.py           # InfluxDB connection testing tool
│           └── 📄 time_unity.py                 # Time unit conversion utilities
└── 📁 static/                                   # Static files for web dashboard
    └── 📄 index.html                            # Web monitoring dashboard HTML
```

### 🔧 Core Components

1. **`EnhancedCryptoPriceProvider`**: Handles Binance WebSocket connections and price data processing, supports caching,
   price change calculation, and statistics. It also provides historical data querying capabilities.
2. **`EnhancedInfluxDBManager`**: Manages InfluxDB connections and optimized batch data writing, supporting background
   processing for efficient data ingestion.
3. **`ConnectionManager` (in `main.py`) / `EnhancedConnectionManager` (in `enhanced_main.py`)**: Manages WebSocket
   client connections, broadcasting real-time data, and orchestrating the data providers. The enhanced version
   integrates Kafka for message queuing.
4. **`CryptoDataAnalyzer`**: Provides historical data analysis, market summaries, trading statistics, price alerts, and
   volume analysis from InfluxDB.
5. **`Config`**: Centralized environment variable configuration management, ensuring secure and flexible deployment.
6. **`SubscriptionRepository`**: Manages the persistence of subscribed symbols in a database (SQLite or PostgreSQL).
7. **`KafkaManager`**: Handles Kafka producer and consumer creation, enabling robust message queuing for data
   distribution.

### 📊 Version Comparison

| Feature Module            | Basic Version (`main.py`)      | Enhanced Version (`enhanced_main.py`) | Notes                                                               |
|---------------------------|--------------------------------|---------------------------------------|---------------------------------------------------------------------|
| Data Fetching             | ✅ EnhancedCryptoPriceProvider  | ✅ EnhancedCryptoPriceProvider         | Both versions use the same advanced data provider.                  |
| Persistent Subscriptions  | ✅ (SQLite / PostgreSQL)        | ✅ (SQLite / PostgreSQL)               | Both versions load/save subscriptions.                              |
| Data Storage              | ✅ InfluxDB (Base + Aggregated) | ✅ InfluxDB (Base + Aggregated)        | Both versions store base and aggregated K-lines.                    |
| Real-time Distribution    | ✅ Simple WebSocket Broadcast   | ✅ WebSocket Broadcast & Kafka         | Enhanced version adds optional Kafka for robust message queuing.    |
| Configuration             | ✅ `config.py`                  | ✅ `config.py`                         | Shared, but the enhanced version uses more configuration options.   |
| API Service               | ✅ (Minimal)                    | ✅ (Rich)                              | Enhanced version adds APIs for history, analysis, stats, etc.       |
| Frontend UI               | ❌                              | ✅ (Web Monitoring Dashboard)          | A key differentiator for the enhanced version.                      |
| Historical Data Query API | ❌                              | ✅ (API for charts)                    | Only the enhanced version provides an API to query historical data. |
| Data Analysis API         | ❌                              | ✅ (Integrated `data_analyzer.py`)     | Only the enhanced version offers analysis reports via API.          |
| Kafka Integration         | ❌                              | ✅ (Optional)                          | An advanced feature available only in the enhanced version.         |

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/tommot20077/tradingview-chart.git
cd person-chart
```

### 2. Configure Environment

Copy the example environment variables file and configure settings:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual configuration (refer to the detailed comments within `.env.example`).

### 3. Install Project Dependencies

Install the project in editable mode. This ensures all local modules are correctly recognized and dependencies are
installed.

```bash
python run.py --install
```

### 4. Test InfluxDB Connection

Before running the main application, test your InfluxDB connection:

```bash
python run.py --test-db
```

This will:

- Test connection to your InfluxDB instance.
- Write sample data.
- Query and display test data.

### 5. Run Server

**Recommended way - using the run script (uses `uvicorn` via console scripts):**

```bash
# Run enhanced server (recommended, includes web dashboard and advanced features)
python run.py --enhanced

# Or run basic server (minimal features)
python run.py --basic

# Check project status and available commands
python run.py --status
```

### 6. Access Web Monitoring Dashboard (Enhanced Version Only)

After running the enhanced server (`python run.py --enhanced`), visit in your browser:

```
http://localhost:8000
```

You will see a real-time monitoring dashboard with:

- 📊 System statistics
- 💰 Live price display
- 🔄 Connection status
- 📈 Performance metrics

### 7. Run Data Analysis

```bash
python run.py --analyze
```

This will execute the `data_analyzer.py` script, which fetches available symbols from InfluxDB and generates a
comprehensive analysis report for the first available symbol.

## API Endpoints

### REST Endpoints

- `GET /` - API information and status (basic version) / Web monitoring dashboard (enhanced version)
- `GET /health` - Health check and system status
- `GET /config` - Current configuration (excluding sensitive data)
- `GET /stats` - Detailed system and crypto provider statistics (enhanced version only)
- `GET /prices` - Get latest cached prices for all subscribed symbols (enhanced version only)
- `POST /symbol/{symbol}/subscribe` - Subscribe to a symbol's price stream
- `POST /symbol/{symbol}/unsubscribe` - Unsubscribe from a symbol's price stream
- `GET /historical/{symbol}` - Get historical K-line data for a symbol (enhanced version only)
- `GET /symbols` - Get list of currently subscribed and cached symbols (enhanced version only)

### WebSocket Endpoint

- `ws://localhost:8000/ws/price` - Real-time price streaming

## Usage Examples

### Subscribe to Additional Symbols

```bash
# Subscribe to Ethereum
curl -X POST "http://localhost:8000/symbol/ethusdt/subscribe"

# Subscribe to Dogecoin
curl -X POST "http://localhost:8000/symbol/dogeusdt/subscribe"
```

### Check System Health

```bash
curl http://localhost:8000/health
```

Response (example for enhanced version):

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

### WebSocket Client Example (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/price');

ws.onopen = function (event) {
    console.log('Connected to price stream');
    // You can send subscription commands from the client (enhanced version only)
    // ws.send('subscribe:ETHUSDT');
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
- `price_change` (Optional, Enhanced Version): Change in price from previous data point.
- `price_change_percent` (Optional, Enhanced Version): Percentage change in price from previous data point.
- `trade_count` (Optional, Enhanced Version): Number of trades in the K-line interval.

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

Use the provided HTTP test file (`src/test_main.http`) with your favorite REST client (e.g., VS Code REST Client
extension, Postman, Insomnia).

### Logging

The application uses structured logging with the following levels:

- `INFO`: General application flow and successful operations.
- `WARNING`: Non-critical issues (e.g., failed WebSocket broadcasts, Kafka not installed).
- `ERROR`: Critical errors that need attention (e.g., InfluxDB connection failure, invalid configuration).

Log format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Adding New Providers

To add support for additional cryptocurrency exchanges:

1. Create a new provider class similar to `CryptoPriceProviderRealtime` or `EnhancedCryptoPriceProviderRealtime`.
2. Implement the `AbstractRealtimeDataProvider` (and optionally `AbstractHistoricalDataProvider`) interface for
   consistency.
3. Update the `config.py` to support new provider-specific settings.
4. Modify the `ConnectionManager` or `EnhancedConnectionManager` to integrate and manage the new data source.

## Security Considerations

- **Environment Variables**: Sensitive data (API tokens, database credentials) are stored in `.env` files and excluded
  from version control (`.gitignore`).
- **Token Exposure**: The `/config` endpoint explicitly excludes sensitive tokens from its response.
- **Input Validation**: Symbol names and other inputs are validated where appropriate to prevent common vulnerabilities.
- **CORS**: Configured to allow all origins by default for development; **for production, restrict `allow_origins` to
  specific domains.**

## Troubleshooting

### Common Issues

1. **InfluxDB Connection Failed**
    - Check your `INFLUXDB_HOST`, `INFLUXDB_TOKEN`, and `INFLUXDB_DATABASE` settings in your `.env` file.
    - Ensure InfluxDB is running and accessible (e.g., check Docker container status if using `docker-compose`).
    - Run `python run.py --test-db` to test connectivity.

2. **Binance WebSocket Connection Issues**
    - Check your internet connectivity.
    - Verify symbol names are valid (e.g., `btcusdt`, `ethusdt` in lowercase).
    - Check Binance API status page for any ongoing issues.

3. **WebSocket Clients Not Receiving Data**
    - Verify the WebSocket endpoint is correct: `ws://localhost:8000/ws/price`.
    - Check the server logs for connection issues or errors during data processing/broadcasting.
    - Ensure the crypto provider is running (check `/health` endpoint).

4. **Kafka or PostgreSQL Errors**
    - Ensure you have installed the optional dependencies: `pip install -e .[kafka]` for
      Kafka, `pip install -e .[postgresql]` for PostgreSQL.
    - Verify Kafka or PostgreSQL services are running and accessible (check `docker-compose-demo.yaml` for default
      ports).
    - Check Kafka broker logs or PostgreSQL database logs for specific error messages.

### Debug Mode

To enable debug logging, modify the logging configuration in `src/main.py` or `src/enhanced_main.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tuning

### InfluxDB Write Optimization

Adjust write options in `EnhancedInfluxDBManager` (in `src/enhanced_crypto_provider.py`) for your needs:

```python
write_options = WriteOptions(
    batch_size=500,  # Increase for higher throughput (default is 200 in enhanced_main.py)
    flush_interval=10_000,  # Reduce for lower latency (default is 5_000)
    max_retries=5  # Adjust based on network reliability
)
```

### WebSocket Connection Limits

The server can handle multiple WebSocket connections. Monitor performance and adjust server resources (CPU, RAM) as
needed.

## License

This project is for educational and research purposes.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Make your changes.
4. Add tests if applicable.
5. Ensure all docstrings and comments are in Traditional Chinese (繁體中文) for consistency.
6. Submit a pull request.

For major changes, please open an issue first to discuss the proposed changes.

### New:

- **K-line Aggregation Data Processing**: Automatically aggregates K-line data from base interval (
  e.g., `config.binance_base_interval`) into larger timeframes, categorized into common and custom intervals.
    1. Common intervals are predefined aggregation scales, directly usable for queries (defined
       in `AGGREGATION_INTERVALS`).
    2. Custom intervals will automatically aggregate data based on the largest common interval factor (e.g., `3d` will
       aggregate 3 daily K-lines).

### Refactor:

- **Logging System**: Added colored logging support, and updated other modules to use the new logging settings.

### Modified:

- **Historical Data Query**: Now includes `limit` and `offset` parameters for paginated queries.
- **User Subscription Interval Settings**: Removed user-defined asset interval settings; intervals are now managed by
  the server, and users can specify custom intervals in requests to display K-line charts of a designated interval.

### Removed:

- `binance_symbol` setting
- Subscription data table interval setting
