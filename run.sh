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

# Check if virtual environment is activated or use uv
ensure_env() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        # Virtual environment is activated, use direct commands
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        # Use uv to run commands
        PYTHON_CMD="uv run python"
        PIP_CMD="uv add"
    fi
}

# Check dependencies
check_deps() {
    print_status "Checking dependencies..."
    
    if [ ! -d ".venv" ] && [[ "$VIRTUAL_ENV" == "" ]]; then
        print_error "Virtual environment not found. Run ./setup.sh first"
        exit 1
    fi
    
    ensure_env
    
    # Check if core library is installed
    if ! $PYTHON_CMD -c "import asset_core" 2>/dev/null; then
        print_warning "asset_core not found. Run ./setup.sh to install dependencies"
        exit 1
    fi
    
    print_success "Dependencies check passed"
}

# Run crypto_single
run_single() {
    print_status "Starting crypto_single..."
    check_deps
    
    if [ -f "./src/crypto_single/main.py" ]; then
        $PYTHON_CMD -m crypto_single.main "$@"
    else
        print_error "crypto_single not properly configured. Run ./setup.sh first"
        exit 1
    fi
}

# Run crypto_cluster
run_cluster() {
    print_status "Starting crypto_cluster..."
    check_deps
    
    print_warning "crypto_cluster not yet implemented in unified structure"
    exit 1
}

# Run tests (using unified test engine)
run_tests() {
    print_status "Running tests using unified test engine..."
    check_deps
    
    # Parse arguments and translate to unified test engine format
    local ENGINE_ARGS=()
    local TEST_SCOPE=""
    local SKIP_QUALITY_CHECKS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --timeout=*)
                ENGINE_ARGS+=("--timeout" "${1#*=}")
                shift
                ;;
            --timeout)
                ENGINE_ARGS+=("--timeout" "$2")
                shift 2
                ;;
            --parallel=*)
                ENGINE_ARGS+=("--parallel" "${1#*=}")
                shift
                ;;
            --parallel)
                ENGINE_ARGS+=("--parallel" "$2")
                shift 2
                ;;
            --parallel-units=*)
                # Convert parallel-units to regular parallel for now
                ENGINE_ARGS+=("--parallel" "${1#*=}")
                shift
                ;;
            --parallel-units)
                # Convert parallel-units to regular parallel for now
                ENGINE_ARGS+=("--parallel" "$2")
                shift 2
                ;;
            --no-cov|--no-coverage)
                ENGINE_ARGS+=("--no-coverage")
                shift
                ;;
            --skip-quality-checks)
                SKIP_QUALITY_CHECKS=true
                print_status "Quality checks will be skipped"
                shift
                ;;
            units|integration|e2e)
                TEST_SCOPE="$1"
                shift
                ;;
            --debug)
                ENGINE_ARGS+=("--debug")
                shift
                ;;
            *)
                # Pass through other arguments to pytest
                ENGINE_ARGS+=("$1")
                shift
                ;;
        esac
    done
    
    # Handle test scope by converting to specific module paths
    if [ -n "$TEST_SCOPE" ]; then
        case "$TEST_SCOPE" in
            units)
                ENGINE_ARGS+=("tests/units")
                print_status "Running $TEST_SCOPE tests"
                ;;
            integration)
                ENGINE_ARGS+=("tests/integration")
                print_status "Running $TEST_SCOPE tests"
                ;;
            e2e)
                ENGINE_ARGS+=("tests/e2e")
                print_status "Running $TEST_SCOPE tests"
                ;;
        esac
    fi
    
    # Add quality checks by default unless skipped
    if [ "$SKIP_QUALITY_CHECKS" = false ]; then
        ENGINE_ARGS+=("--with-quality-checks")
        print_status "Including quality checks (linting, format checking, type checking)"
    fi
    
    # Execute unified test engine
    if bash scripts/test-engine.sh "${ENGINE_ARGS[@]}"; then
        print_success "Tests completed successfully"
    else
        print_error "Tests failed"
        return 1
    fi
}

# Run linting
run_lint() {
    print_status "Running code quality checks..."
    check_deps
    
    print_status "Running ruff format..."
    uv run ruff format .
    
    print_status "Running ruff check..."
    uv run ruff check .
    
    print_status "Running mypy..."
    uv run mypy .
    
    print_success "Code quality checks completed"
}

# Install dependencies
install_deps() {
    print_status "Installing dependencies..."
    ./setup.sh "$@"
}

# Show application status
show_status() {
    print_status "TradingChart Project Status"
    echo "============================"
    
    # Check virtual environment
    if [ -d ".venv" ]; then
        print_success "Virtual environment: .venv ✓"
    else
        print_error "Virtual environment: Not found ✗"
    fi
    
    # Check if activated
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "Environment: Activated ✓"
    else
        print_warning "Environment: Not activated (will use 'uv run')"
    fi
    
    # Check components
    echo ""
    echo "Components:"
    
    ensure_env
    
    # Check asset_core
    if $PYTHON_CMD -c "import asset_core" 2>/dev/null; then
        print_success "  asset_core: Installed ✓"
    else
        print_error "  asset_core: Not installed ✗"
    fi
    
    # Check crypto_single
    if [ -f "./src/crypto_single/pyproject.toml" ]; then
        if $PYTHON_CMD -c "import crypto_single" 2>/dev/null; then
            print_success "  crypto_single: Installed ✓"
        else
            print_warning "  crypto_single: Configured but not installed"
        fi
    else
        print_warning "  crypto_single: Not configured"
    fi
    
    # Check crypto_cluster
    if [ -f "./src/crypto_cluster/pyproject.toml" ]; then
        if $PYTHON_CMD -c "import crypto_cluster" 2>/dev/null; then
            print_success "  crypto_cluster: Installed ✓"
        else
            print_warning "  crypto_cluster: Configured but not installed"
        fi
    else
        print_warning "  crypto_cluster: Not configured"
    fi
    
    echo ""
    echo "Usage: ./run.sh [command] [options]"
    echo "Run './run.sh --help' for more information"
}

# Show help
show_help() {
    cat << EOF
TradingChart Project Runner
===========================

Usage: $0 [command] [options]

Commands:
  single [args]     Run crypto_single application
  cluster [args]    Run crypto_cluster application
  test [args]       Run tests (with optional pytest arguments and new features)
  lint              Run code quality checks (ruff + mypy)
  install [args]    Install dependencies (calls setup.sh)
  status            Show project status
  deps              Check dependencies
  help, --help, -h  Show this help message

Test Command Options:
  Basic Usage:
    test                          # Run all tests with quality checks & coverage
    test units                    # Run only unit tests
    test integration              # Run only integration tests
    test e2e                      # Run only end-to-end tests
    test [path]                   # Run specific test file/directory

  Quality & Performance Options:
    --skip-quality-checks         # Skip linting, format checking, and type checking
    --timeout=SECONDS             # Set timeout per test (e.g., --timeout=30)
    --parallel=N                  # Run tests in parallel with N workers
    --parallel-units=N            # Run only unit tests in parallel with N workers
    --no-cov, --no-coverage      # Disable coverage reporting

  Test Categories:
    units:        Fast, isolated tests with mocks (can run in parallel)
    integration:  Tests with component interactions (run serially)
    e2e:          End-to-end workflow tests (run serially)

Examples:
  Basic Commands:
    $0 single                                    # Run crypto_single
    $0 cluster                                   # Run crypto_cluster
    $0 test                                      # Run all tests with quality checks & coverage
    $0 test units                                # Run unit tests only
    $0 test integration                          # Run integration tests only
    $0 test --skip-quality-checks                # Run tests without quality checks
    $0 lint                                      # Run code quality checks only
    $0 install                                   # Install all dependencies
    $0 install --core-only                       # Install only core library
    $0 status                                    # Show project status

  Test Performance:
    $0 test --timeout=60                         # Run tests with quality checks & 60s timeout
    $0 test --skip-quality-checks --timeout=60   # Run tests without quality checks, 60s timeout
    $0 test units --parallel-units=4             # Run unit tests with 4 parallel workers
    $0 test --parallel=2 --timeout=30            # Run all tests in parallel with timeout
    $0 test integration --timeout=120            # Run integration tests with 2min timeout
    $0 test --no-cov                            # Run tests without coverage (but with quality checks)

  Test Targeting:
    $0 test src/asset_core/tests/units/config/                   # Run specific test directory
    $0 test src/asset_core/tests/units/models/test_kline.py      # Run specific test file
    $0 test units --timeout=30 --no-cov           # Fast unit test run (with quality checks)

  Fast Development Testing:
    $0 test units --skip-quality-checks --parallel-units=4 --timeout=60 --no-cov
        # Fastest unit tests: no quality checks, parallel execution, 60s timeout, no coverage
    
    $0 test --skip-quality-checks --no-cov
        # Fast all tests: skip quality checks and coverage for speed
    
    $0 test integration --timeout=300
        # Thorough integration testing: 5min timeout per test (includes quality checks)
    
    $0 test --parallel=logical --timeout=120
        # Full test suite: use logical CPU count, 2min timeout per test

Performance Notes:
  - Unit tests are safe for parallel execution (isolated with mocks)
  - Integration/E2E tests run serially to avoid resource conflicts
  - Use --parallel-units for fastest development feedback
  - Use --timeout to catch hanging tests early
  - Omit --cov for faster test runs during development

Environment:
  The script automatically detects if you're in a virtual environment.
  If not activated, it will use 'uv run' to execute commands.

  To activate the virtual environment manually:
    source .venv/bin/activate

EOF
}

# Main command dispatcher
main() {
    case "${1:-status}" in
        single)
            shift
            run_single "$@"
            ;;
        cluster)
            shift
            run_cluster "$@"
            ;;
        test)
            shift
            run_tests "$@"
            ;;
        lint|format)
            run_lint
            ;;
        install|setup)
            shift
            install_deps "$@"
            ;;
        deps|check)
            check_deps
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"