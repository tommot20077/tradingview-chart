# TradingChart Monorepo

A comprehensive asset trading data infrastructure built with modern Python practices.

## 🏗️ Architecture

This monorepo contains:
- **asset_core**: Core library with abstractions and utilities
- **crypto_single**: Single-instance asset data ingestion application
- **crypto_cluster**: (Placeholder) Distributed cluster version

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- InfluxDB 2.x (for time-series data storage)

### Setup Development Environment

```bash
# One-step setup (recommended)
./setup.sh

# Or setup manually with uv
uv venv
source .venv/bin/activate  # Unix/macOS
# .venv\Scripts\activate   # Windows
uv pip install -e ./src/asset_core[dev]
uv pip install -e ./src/crypto_single[dev]
```

### Configuration

1. Copy `.env.example` to `.env` in the application directory
2. Configure your exchange API keys and InfluxDB connection

## 📁 Project Structure

```
/
├── .github/workflows/      # CI/CD pipelines
├── src/
│   ├── asset_core/        # Core abstractions and utilities
│   │   ├── asset_core/
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   ├── models/
│   │   │   ├── events/
│   │   │   ├── providers/
│   │   │   ├── storage/
│   │   │   ├── network/
│   │   │   └── observability/
│   │   └── tests/
│   │
│   ├── crypto_single/     # Single-instance application
│   │   ├── crypto_single/
│   │   │   ├── providers/
│   │   │   ├── storage/
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   └── security/
│   │   └── tests/
│   └── crypto_cluster/    # Distributed version (future)
├── pyproject.toml         # Root development tools config
└── README.md
```

## 🔒 Security Features

- **API Key Encryption**: All exchange API keys are encrypted at rest
- **Admin Token Protection**: Management endpoints require authentication
- **Environment-based Configuration**: Sensitive data stored in environment variables

## 🧪 Testing & Quality Assurance

```bash
# Run all tests with quality checks (recommended)
./run.sh test

# Fast development testing (skip quality checks)
./run.sh test --skip-quality-checks

# Run specific test types
./run.sh test units                    # Unit tests only
./run.sh test integration              # Integration tests only
./run.sh test specific/test/path.py    # Specific test file

# Quality checks only
./run.sh lint

# Fast parallel unit tests for development
./run.sh test units --skip-quality-checks --parallel-units=4 --no-cov
```

The testing system now includes:
- **Automated Quality Checks**: Linting, formatting, and type checking run by default
- **Unified Test Engine**: Ensures local and CI testing are identical
- **Smart Module Detection**: Automatically detects which modules are ready for testing
- **Parallel Execution**: Support for parallel unit test execution

## 📊 Observability

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Prometheus Metrics**: Built-in metrics for monitoring
- **Health Checks**: `/health` endpoint for service monitoring

## 🚢 Deployment

### GitHub Releases

The project uses GitHub Actions for automated releases:

1. **Core Library**: Tag with `asset-core-v*` pattern
2. **Application**: Tag with `crypto-single-v*` pattern

### Docker (Optional)

```bash
# Build image
docker build -t crypto-single:latest -f apps/crypto_single/Dockerfile .

# Run container
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  crypto-single:latest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.