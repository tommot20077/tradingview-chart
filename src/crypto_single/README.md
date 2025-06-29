# Crypto Single Application

Single instance cryptocurrency data ingestion and processing service built on the `asset_core` foundation.

## Overview

Crypto Single is responsible for:
- Single instance trading data collection and processing
- Implementation of all abstract interfaces from `asset_core`
- REST API and management interface
- Data persistence and real-time streaming

## Architecture

```
crypto_single/
├── providers/          # Data provider implementations
├── storage/           # Storage implementations  
├── services/          # Business service layer
├── api/              # REST API endpoints
├── events/           # Event handling implementations
├── workers/          # Background workers
├── config/           # Application configuration
└── security/         # Security related modules
```

## Quick Start

### Prerequisites
- Python 3.12+
- uv package manager
- PostgreSQL (or SQLite for development)
- Redis (optional)

### Installation

```bash
# Install dependencies
cd src/crypto_single
uv sync

# Copy environment configuration
cp .env.example .env
# Edit .env with your settings

# Run the application
uv run crypto-single
```

### Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=crypto_single

# Type checking
uv run mypy crypto_single

# Format code
uv run ruff format crypto_single

# Lint code
uv run ruff check crypto_single
```

## Configuration

See `.env.example` for all available configuration options.

Key configuration areas:
- **Database**: PostgreSQL or SQLite connection
- **Redis**: Optional caching and pub/sub
- **API**: FastAPI server settings
- **Security**: JWT and authentication
- **Binance**: Exchange API credentials
- **Monitoring**: Metrics and logging

## API Documentation

Once running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License