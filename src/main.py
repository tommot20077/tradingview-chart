import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.websockets import WebSocket

from config import config
from crypto_price_provider import CryptoPriceProvider, InfluxDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Store connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.crypto_provider: CryptoPriceProvider = None
        self.loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Broadcast message to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        # Create a list to track failed connections
        failed_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                failed_connections.append(connection)
        
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
        """Initialize and start the crypto price provider"""
        try:
            # Validate configuration
            if not config.validate():
                logger.error("Invalid configuration. Please check your .env file.")
                raise ValueError("Invalid configuration")
            
            # Create InfluxDB manager
            influxdb_manager = InfluxDBManager(
                host=config.influxdb_host,
                token=config.influxdb_token,
                database=config.influxdb_database
            )
            
            # Create crypto price provider with message callback for WebSocket broadcasting
            self.crypto_provider = CryptoPriceProvider(
                influxdb_manager=influxdb_manager,
                message_callback=self.sync_broadcast
            )
            
            # Start the provider
            self.crypto_provider.start()
            
            # Subscribe to configured symbol
            self.crypto_provider.subscribe_symbol(
                symbol=config.binance_symbol,
                interval=config.binance_interval
            )
            
            logger.info(f"Started crypto price provider for {config.binance_symbol}")
            
        except Exception as e:
            logger.error(f"Failed to start crypto price provider: {e}")
            raise

    def stop_crypto_provider(self):
        """Stop the crypto price provider"""
        if self.crypto_provider:
            try:
                self.crypto_provider.stop()
                logger.info("Stopped crypto price provider")
            except Exception as e:
                logger.error(f"Error stopping crypto price provider: {e}")

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    try:
        logger.info("Starting application...")
        
        # Store the event loop for sync broadcasting
        manager.loop = asyncio.get_running_loop()
        
        # Start crypto price provider
        manager.start_crypto_provider()
        
        logger.info("Application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        manager.stop_crypto_provider()
        logger.info("Application shutdown complete")

app = FastAPI(
    title="Crypto Price Stream API",
    description="Real-time cryptocurrency price streaming with InfluxDB storage",
    version="1.0.0",
    lifespan=lifespan
)

@app.websocket("/ws/price")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for any message
            # In a real application, you might handle client commands here
            await websocket.receive_text()
    except Exception as e:
        logger.info(f"WebSocket connection closed: {e}")
    finally:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Crypto Price Stream Server",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/price",
            "health": "/health",
            "config": "/config"
        },
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    crypto_provider_status = "running" if manager.crypto_provider else "stopped"
    
    return {
        "status": "healthy",
        "crypto_provider": crypto_provider_status,
        "active_websocket_connections": len(manager.active_connections),
        "subscribed_symbols": list(manager.crypto_provider.subscribed_symbols) if manager.crypto_provider else []
    }

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
        # Note: influxdb_token is excluded for security
    }

@app.post("/symbol/{symbol}/subscribe")
async def subscribe_symbol(symbol: str, interval: str = "1m"):
    """Subscribe to a new symbol's price stream"""
    if not manager.crypto_provider:
        return {"error": "Crypto provider not initialized"}
    
    try:
        manager.crypto_provider.subscribe_symbol(symbol, interval)
        return {
            "status": "success",
            "message": f"Subscribed to {symbol} with {interval} interval"
        }
    except Exception as e:
        logger.error(f"Failed to subscribe to {symbol}: {e}")
        return {"error": str(e)}

@app.post("/symbol/{symbol}/unsubscribe")
async def unsubscribe_symbol(symbol: str, interval: str = "1m"):
    """Unsubscribe from a symbol's price stream"""
    if not manager.crypto_provider:
        return {"error": "Crypto provider not initialized"}
    
    try:
        manager.crypto_provider.unsubscribe_symbol(symbol, interval)
        return {
            "status": "success",
            "message": f"Unsubscribed from {symbol} with {interval} interval"
        }
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {config.api_host}:{config.api_port}")
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level="info"
    )
