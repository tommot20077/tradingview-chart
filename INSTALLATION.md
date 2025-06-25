# TradingChart Installation Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Install uv (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Complete Installation
```bash
# Clone the repository and navigate to it
git clone <repository-url>
cd TradingChart

# Run the setup script
./setup.sh
```

## 📦 Installation Options

### Full Installation (Recommended)
```bash
./setup.sh
```
This installs:
- Core library (`asset_core`)
- All applications (`crypto_single`, `crypto_cluster`)
- Development dependencies
- Test dependencies

### Core Library Only
```bash
./setup.sh --core-only
```

### Applications Only
```bash
./setup.sh --apps-only
```

## 🔧 Project Structure

```
TradingChart/
├── src/
│   ├── asset_core/          # Core library
│   │   ├── asset_core/      # Source code
│   │   ├── tests/           # Tests
│   │   └── pyproject.toml   # Core dependencies
│   ├── crypto_single/       # Single crypto service
│   │   ├── crypto_single/   # Source code
│   │   ├── tests/           # Tests
│   │   └── pyproject.toml   # Application dependencies
│   └── crypto_cluster/      # Clustered crypto service
│       ├── crypto_cluster/  # Source code
│       ├── tests/           # Tests
│       └── pyproject.toml   # Application dependencies
├── .venv/                   # Virtual environment (shared)
├── setup.sh                 # Installation script
├── run.sh                   # Application runner
├── install_deps.sh          # Legacy installation (fixed)
├── pyproject.toml           # Root project configuration
└── uv.lock                  # Dependency lock file
```

## 🏃‍♂️ Running Applications

### Using the Run Script
```bash
# Show project status
./run.sh status

# Run crypto_single
./run.sh single

# Run crypto_cluster
./run.sh cluster

# Run with arguments
./run.sh single --config config.json --verbose
```

### Direct Execution (if venv activated)
```bash
# Activate virtual environment
source .venv/bin/activate

# Run applications
cd src/crypto_single && python -m crypto_single
cd src/crypto_cluster && python -m crypto_cluster
```

### Using uv (if venv not activated)
```bash
# Run applications with uv
uv run --directory src/crypto_single python -m crypto_single
uv run --directory src/crypto_cluster python -m crypto_cluster
```

## 🧪 Testing

### Run All Tests
```bash
./run.sh test
```

### Run Specific Tests
```bash
./run.sh test src/asset_core/tests/test_models.py
./run.sh test -k "test_websocket"
```

### Run Tests with Coverage
```bash
./run.sh test --cov-report=html
```

## 🔍 Code Quality

### Run All Quality Checks
```bash
./run.sh lint
```

This runs:
- `ruff format .` - Code formatting
- `ruff check .` - Linting
- `mypy .` - Type checking

### Individual Commands
```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Type checking
uv run mypy .
```

## 🔄 Development Workflow

### Daily Development
```bash
# 1. Check project status
./run.sh status

# 2. Install any new dependencies
./run.sh install

# 3. Run tests
./run.sh test

# 4. Check code quality
./run.sh lint

# 5. Run application
./run.sh single
```

### Adding New Dependencies

#### To Core Library
```bash
# Navigate to core library
cd src/asset_core

# Add dependency
uv add "new-package>=1.0.0"

# Or add development dependency
uv add --dev "new-dev-package>=1.0.0"
```

#### To Applications
```bash
# Navigate to application
cd src/crypto_single

# Add dependency
uv add "new-package>=1.0.0"
```

## 🌐 Virtual Environment Strategy

### Recommended: Single Shared venv (Current Setup)
**Advantages:**
- ✅ Simplified dependency management
- ✅ Consistent versions across components
- ✅ Reduced disk space usage
- ✅ Easier development workflow
- ✅ Works seamlessly with uv.lock

### Alternative: Individual venvs per Component
If you prefer isolated environments:

```bash
# Core library
cd src/asset_core
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .[dev]

# Each application
cd ../crypto_single
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e . -e ../asset_core
```

**Note:** The current setup uses a shared venv which is the recommended approach for monorepos.

## 🛠️ Troubleshooting

### Common Issues

#### "Virtual environment not found"
```bash
# Re-run setup
./setup.sh
```

#### "asset_core not found"
```bash
# Check if core library is installed
./run.sh deps

# Reinstall if needed
./setup.sh --core-only
```

#### "Command not found: uv"
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

#### Permission denied on scripts
```bash
# Make scripts executable
chmod +x setup.sh run.sh
```

### Dependency Conflicts
```bash
# Clean and reinstall
rm -rf .venv uv.lock
./setup.sh
```

## 📋 Available Commands

### Setup Script (`./setup.sh`)
- `./setup.sh` - Full installation
- `./setup.sh --core-only` - Install only core library
- `./setup.sh --apps-only` - Install only applications
- `./setup.sh --help` - Show help

### Run Script (`./run.sh`)
- `./run.sh status` - Show project status
- `./run.sh single [args]` - Run crypto_single
- `./run.sh cluster [args]` - Run crypto_cluster
- `./run.sh test [args]` - Run tests
- `./run.sh lint` - Run code quality checks
- `./run.sh install [args]` - Install dependencies
- `./run.sh deps` - Check dependencies
- `./run.sh help` - Show help

## 🔒 Security Notes

- Environment variables are used for sensitive configuration
- API keys and secrets are never logged
- All input data is validated using Pydantic models
- Dependencies are locked with `uv.lock` for reproducible builds

## 📝 Next Steps

1. **First time setup**: Run `./setup.sh`
2. **Check status**: Run `./run.sh status`
3. **Run tests**: Run `./run.sh test`
4. **Start development**: Run `./run.sh single` or `./run.sh cluster`
5. **Read the docs**: Check `CLAUDE.md` for development guidelines

## 🤝 Contributing

Before submitting changes:
1. Run `./run.sh test` to ensure tests pass
2. Run `./run.sh lint` to check code quality
3. Follow the guidelines in `CLAUDE.md`