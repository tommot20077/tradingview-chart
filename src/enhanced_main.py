import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.websockets import WebSocket
from fastapi.responses import HTMLResponse

from config import config
from enhanced_crypto_provider import EnhancedCryptoPriceProvider, EnhancedInfluxDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: EnhancedCryptoPriceProvider = None
        self.loop = None
        self.connection_stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "failed_sends": 0
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_stats["total_connections"] += 1
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}, Total: {self.connection_stats['total_connections']}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Broadcast message to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        failed_connections = []
        successful_sends = 0
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                successful_sends += 1
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                failed_connections.append(connection)
                self.connection_stats["failed_sends"] += 1
        
        self.connection_stats["messages_sent"] += successful_sends
        
        # Remove failed connections
        for failed_connection in failed_connections:
            self.disconnect(failed_connection)

    def sync_broadcast(self, message: str):
        """Thread-safe method to broadcast message from sync context"""
        if self.loop is None or not self.loop.is_running():
            return
        
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)
        except Exception as e:
            logger.error(f"Failed to schedule broadcast: {e}")

    def start_crypto_provider(self):
        """Initialize and start the enhanced crypto price provider"""
        try:
            if not config.validate():
                logger.error("Invalid configuration. Please check your .env file.")
                raise ValueError("Invalid configuration")
            
            # Create enhanced InfluxDB manager with larger batch size for better performance
            influxdb_manager = EnhancedInfluxDBManager(
                host=config.influxdb_host,
                token=config.influxdb_token,
                database=config.influxdb_database,
                batch_size=200  # Increased batch size for better performance
            )
            
            # Create enhanced crypto price provider
            self.crypto_provider = EnhancedCryptoPriceProvider(
                influxdb_manager=influxdb_manager,
                message_callback=self.sync_broadcast
            )
            
            self.crypto_provider.start()
            
            # Subscribe to configured symbol
            self.crypto_provider.subscribe_symbol(
                symbol=config.binance_symbol,
                interval=config.binance_interval
            )
            
            logger.info(f"Started enhanced crypto price provider for {config.binance_symbol}")
            
        except Exception as e:
            logger.error(f"Failed to start enhanced crypto price provider: {e}")
            raise

    def stop_crypto_provider(self):
        """Stop the enhanced crypto price provider"""
        if self.crypto_provider:
            try:
                self.crypto_provider.stop()
                logger.info("Stopped enhanced crypto price provider")
            except Exception as e:
                logger.error(f"Error stopping enhanced crypto price provider: {e}")

manager = EnhancedConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    try:
        logger.info("Starting enhanced crypto application...")
        
        manager.loop = asyncio.get_running_loop()
        manager.start_crypto_provider()
        
        logger.info("Enhanced crypto application started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start enhanced crypto application: {e}")
        raise
    
    finally:
        logger.info("Shutting down enhanced crypto application...")
        manager.stop_crypto_provider()
        logger.info("Enhanced crypto application shutdown complete")

app = FastAPI(
    title="Enhanced Crypto Price Stream API",
    description="Real-time cryptocurrency price streaming with enhanced InfluxDB storage and monitoring",
    version="2.0.0",
    lifespan=lifespan
)

@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint for real-time price streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and handle potential client commands
            message = await websocket.receive_text()
            
            # Handle client commands (optional feature)
            if message.startswith("subscribe:"):
                symbol = message.split(":")[1].upper()
                if manager.crypto_provider:
                    manager.crypto_provider.subscribe_symbol(symbol)
                    await websocket.send_text(f"Subscribed to {symbol}")
                    
            elif message.startswith("unsubscribe:"):
                symbol = message.split(":")[1].upper()
                if manager.crypto_provider:
                    manager.crypto_provider.unsubscribe_symbol(symbol)
                    await websocket.send_text(f"Unsubscribed from {symbol}")
                    
    except Exception as e:
        logger.info(f"WebSocket connection closed: {e}")
    finally:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Enhanced root endpoint with dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Crypto Price Stream</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #1a1a1a; color: #ffffff; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #2d2d2d; padding: 20px; border-radius: 8px; border-left: 4px solid #4CAF50; }
            .stat-title { font-size: 14px; color: #999; margin-bottom: 5px; }
            .stat-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
            .prices-container { background: #2d2d2d; padding: 20px; border-radius: 8px; }
            .price-item { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #444; }
            .symbol { font-weight: bold; color: #4CAF50; }
            .price { color: #ffffff; }
            .change { padding: 5px 10px; border-radius: 4px; font-size: 12px; }
            .positive { background-color: #4CAF50; }
            .negative { background-color: #f44336; }
            .endpoints { background: #2d2d2d; padding: 20px; border-radius: 8px; margin-top: 20px; }
            .endpoint { margin: 10px 0; padding: 10px; background: #3d3d3d; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Enhanced Crypto Price Stream Server</h1>
                <p>Real-time cryptocurrency data with InfluxDB storage</p>
            </div>
            
            <div class="stats-grid" id="stats-grid">
                <!-- Stats will be loaded here -->
            </div>
            
            <div class="prices-container">
                <h3>Real-time Prices</h3>
                <div id="prices">
                    <!-- Prices will be loaded here -->
                </div>
            </div>
            
            <div class="endpoints">
                <h3>API Endpoints</h3>
                <div class="endpoint"><strong>WebSocket:</strong> ws://localhost:8000/ws/price</div>
                <div class="endpoint"><strong>Health Check:</strong> <a href="/health">/health</a></div>
                <div class="endpoint"><strong>Statistics:</strong> <a href="/stats">/stats</a></div>
                <div class="endpoint"><strong>Latest Prices:</strong> <a href="/prices">/prices</a></div>
            </div>
        </div>
        
        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const stats = await response.json();
                    
                    const statsGrid = document.getElementById('stats-grid');
                    statsGrid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-title">Messages Processed</div>
                            <div class="stat-value">${stats.crypto_provider?.messages_processed || 0}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">Active Connections</div>
                            <div class="stat-value">${stats.active_websocket_connections}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">InfluxDB Writes</div>
                            <div class="stat-value">${stats.crypto_provider?.influxdb_stats?.total_writes || 0}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-title">Uptime</div>
                            <div class="stat-value">${Math.round(stats.crypto_provider?.uptime_seconds || 0)}s</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Failed to load stats:', error);
                }
            }
            
            async function loadPrices() {
                try {
                    const response = await fetch('/prices');
                    const prices = await response.json();
                    
                    const pricesDiv = document.getElementById('prices');
                    pricesDiv.innerHTML = Object.entries(prices).map(([symbol, data]) => `
                        <div class="price-item">
                            <span class="symbol">${symbol}</span>
                            <span class="price">$${parseFloat(data.price).toFixed(4)}</span>
                            <span class="change ${(data.price_change_percent || 0) >= 0 ? 'positive' : 'negative'}">
                                ${(data.price_change_percent || 0).toFixed(2)}%
                            </span>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('Failed to load prices:', error);
                }
            }
            
            // Load data on page load
            loadStats();
            loadPrices();
            
            // Refresh data every 5 seconds
            setInterval(() => {
                loadStats();
                loadPrices();
            }, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    crypto_provider_status = "stopped"
    provider_stats = {}
    
    if manager.crypto_provider:
        crypto_provider_status = "running"
        provider_stats = manager.crypto_provider.get_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crypto_provider": crypto_provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "connection_stats": manager.connection_stats,
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols) if manager.crypto_provider else [],
        "provider_stats": provider_stats
    }

@app.get("/stats")
async def get_detailed_stats():
    """Get detailed system statistics"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="Crypto provider not running")
    
    crypto_stats = manager.crypto_provider.get_stats()
    
    return {
        "system": {
            "active_websocket_connections": len(manager.active_connections),
            "connection_stats": manager.connection_stats,
            "uptime": datetime.now(timezone.utc).isoformat()
        },
        "crypto_provider": crypto_stats,
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols)
    }

@app.get("/prices")
async def get_latest_prices():
    """Get latest cached prices for all symbols"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="Crypto provider not running")
    
    return manager.crypto_provider.get_latest_prices()

@app.get("/config")
async def get_config():
    """Get current configuration (excluding sensitive data)"""
    return {
        "binance_symbol": config.binance_symbol,
        "binance_interval": config.binance_interval,
        "api_host": config.api_host,
        "api_port": config.api_port,
        "influxdb_host": config.influxdb_host,
        "influxdb_database": config.influxdb_database
    }

@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """Subscribe to a new symbol's price stream"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="Crypto provider not initialized")
    
    try:
        manager.crypto_provider.subscribe_symbol(symbol.upper(), interval)
        return {
            "status": "success",
            "message": f"Subscribed to {symbol.upper()} with {interval} interval",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to subscribe to {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """Unsubscribe from a symbol's price stream"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="Crypto provider not initialized")
    
    try:
        manager.crypto_provider.unsubscribe_symbol(symbol.upper(), interval)
        return {
            "status": "success",
            "message": f"Unsubscribed from {symbol.upper()} with {interval} interval",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/symbols")
async def get_subscribed_symbols():
    """Get list of currently subscribed symbols"""
    if not manager.crypto_provider:
        raise HTTPException(status_code=503, detail="Crypto provider not running")
    
    return {
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols),
        "cached_symbols": list(manager.crypto_provider.get_latest_prices().keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting enhanced server on {config.api_host}:{config.api_port}")
    uvicorn.run(
        "enhanced_main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level="info"
    )
