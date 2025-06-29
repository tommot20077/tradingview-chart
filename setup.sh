#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install uv first:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_success "uv is installed"
}

# Setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d ".venv" ]; then
        print_status "Creating virtual environment..."
        uv venv
    fi
    
    print_success "Virtual environment ready"
}

# Install core library
install_core() {
    print_status "Installing asset_core library..."
    
    # With unified pyproject.toml, no need to install separately
    print_success "asset_core installed via unified project"
}

# Install applications
install_apps() {
    print_status "Applications available..."
    
    # With unified pyproject.toml, applications are already configured
    print_success "crypto_single and crypto_cluster available via unified project"
}

# Create crypto_single configuration
create_crypto_single_config() {
    mkdir -p ./src/crypto_single/crypto_single
    
    cat > ./src/crypto_single/pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "crypto-single"
version = "0.1.0"
description = "Single crypto data ingestion service"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "TradingChart Team"},
]

dependencies = [
    "asset-core",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.1",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["crypto_single*"]
exclude = ["tests*"]

[tool.uv.sources]
asset-core = { path = "../asset_core", editable = true }
EOF

    # Create basic structure
    touch ./src/crypto_single/crypto_single/__init__.py
    touch ./src/crypto_single/crypto_single/main.py
    mkdir -p ./src/crypto_single/tests
    touch ./src/crypto_single/tests/__init__.py
    
    print_success "crypto_single configuration created"
}

# Create crypto_cluster structure
create_crypto_cluster_structure() {
    mkdir -p ./src/crypto_cluster/crypto_cluster
    
    cat > ./src/crypto_cluster/pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "crypto-cluster"
version = "0.1.0"
description = "Clustered crypto data ingestion service"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "TradingChart Team"},
]

dependencies = [
    "asset-core",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.1",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["crypto_cluster*"]
exclude = ["tests*"]

[tool.uv.sources]
asset-core = { path = "../asset_core", editable = true }
EOF

    # Create basic structure
    touch ./src/crypto_cluster/crypto_cluster/__init__.py
    touch ./src/crypto_cluster/crypto_cluster/main.py
    mkdir -p ./src/crypto_cluster/tests
    touch ./src/crypto_cluster/tests/__init__.py
    
    print_success "crypto_cluster structure created"
}

# Sync root project
sync_root() {
    print_status "Syncing root project dependencies..."
    uv sync
    print_success "Root project synchronized"
}

# Run setup
main() {
    echo "🚀 TradingChart Project Setup"
    echo "=============================="
    
    check_uv
    setup_venv
    install_core
    install_apps
    sync_root
    
    echo ""
    print_success "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Activate environment: source .venv/bin/activate"
    echo "  2. Run applications: ./run.sh --help"
    echo "  3. Run tests: ./run.sh test"
    echo "  4. Check code quality: ./run.sh lint"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --core-only   Install only core library"
        echo "  --apps-only   Install only applications"
        exit 0
        ;;
    --core-only)
        check_uv
        setup_venv
        sync_root
        ;;
    --apps-only)
        print_warning "--apps-only is deprecated with unified project structure"
        sync_root
        ;;
    *)
        main
        ;;
esac