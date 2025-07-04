#!/bin/bash

# Unified Test Engine
# Single source of truth for all testing logic
# Used by both ./run.sh test and CI

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
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

print_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${BLUE}🔍 DEBUG: $1${NC}" >&2
    fi
}

# Default configuration
PYTHON_CMD="uv run python"
COVERAGE_ENABLED=true
PARALLEL=""
TIMEOUT=""
CI_MODE=false
TEST_MODULES=""
TEST_ARGS=()
RUN_QUALITY_CHECKS=false

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ci-mode)
                CI_MODE=true
                RUN_QUALITY_CHECKS=true
                print_debug "CI mode enabled with quality checks"
                shift
                ;;
            --no-coverage)
                COVERAGE_ENABLED=false
                print_debug "Coverage disabled"
                shift
                ;;
            --parallel)
                PARALLEL="$2"
                print_debug "Parallel execution with $PARALLEL workers"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                print_debug "Test timeout set to $TIMEOUT seconds"
                shift 2
                ;;
            --modules)
                TEST_MODULES="$2"
                print_debug "Testing specific modules: $TEST_MODULES"
                shift 2
                ;;
            --with-quality-checks)
                RUN_QUALITY_CHECKS=true
                print_debug "Quality checks enabled"
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                TEST_ARGS+=("$1")
                shift
                ;;
        esac
    done
}

# Show help message
show_help() {
    echo "Unified Test Engine"
    echo "=================="
    echo ""
    echo "Usage: $0 [options] [pytest-args...]"
    echo ""
    echo "Options:"
    echo "  --ci-mode           Enable CI mode (includes quality checks)"
    echo "  --with-quality-checks Run linting and type checking before tests"
    echo "  --no-coverage       Disable coverage reporting"
    echo "  --parallel N        Run tests in parallel with N workers"
    echo "  --timeout N         Set test timeout in seconds"
    echo "  --modules \"mod1 mod2\" Test specific modules"
    echo "  --debug             Enable debug output"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Test all ready modules"
    echo "  $0 --ci-mode                         # CI testing mode"
    echo "  $0 --modules \"asset_core\"             # Test specific module"
    echo "  $0 --parallel 4                      # Parallel testing"
    echo "  $0 tests/units/test_models.py        # Test specific file"
}

# Detect ready modules
detect_modules() {
    print_debug "Detecting ready modules..."
    
    local modules
    if ! modules=$(bash "$SCRIPT_DIR/detect-modules.sh" --src-dir "$PROJECT_ROOT/src"); then
        print_error "Failed to detect ready modules"
        return 1
    fi
    
    if [ -z "$modules" ]; then
        print_error "No modules ready for testing"
        return 1
    fi
    
    echo "$modules"
}

# Check if uv is available
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install uv first:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
    print_debug "uv is available"
}

# Run quality checks (linting and type checking)
run_quality_checks() {
    print_status "Running Quality Checks"
    echo "======================="
    
    # Run linting
    print_status "Running linting (ruff check)"
    if ! uv run ruff check .; then
        print_error "Linting failed - check the output above for specific issues"
        return 1
    fi
    print_success "Linting passed"
    
    # Run format checking
    print_status "Running format checking (ruff format)"
    if ! uv run ruff format --check .; then
        print_error "Format checking failed - run 'uv run ruff format .' to fix formatting issues"
        return 1
    fi
    print_success "Format checking passed"
    
    # Run type checking
    print_status "Running type checking (mypy)"
    if ! uv run mypy .; then
        print_error "Type checking failed - check the output above for specific type errors"
        return 1
    fi
    print_success "Type checking passed"
    
    echo "" # Add spacing
    return 0
}

# Process test arguments to handle direct pytest paths
process_test_args() {
    local processed_args=()
    
    for arg in "${TEST_ARGS[@]}"; do
        # Check if argument looks like a path (contains / and doesn't start with -)
        if [[ "$arg" == *"/"* && ! "$arg" == -* ]]; then
            # If it's already a tests/ path, keep as is (direct pytest path)
            if [[ "$arg" == "tests/"* ]]; then
                processed_args+=("$arg")
                print_debug "Direct test path: $arg"
            else
                # Not a test path, keep as is (probably a pytest option)
                processed_args+=("$arg")
            fi
        else
            # Not a path, keep as is (pytest option or argument)
            processed_args+=("$arg")
        fi
    done
    
    # Update TEST_ARGS with processed paths
    TEST_ARGS=("${processed_args[@]}")
}

# Run tests directly with pytest (simplified approach)
run_tests_directly() {
    print_status "Running tests directly with pytest"
    
    # Stay in project root (unified structure with single pyproject.toml)
    print_debug "Working in project root for unified structure"
    
    # Build test command
    local test_cmd="$PYTHON_CMD -m pytest"
    
    # Add timeout if specified
    if [ -n "$TIMEOUT" ]; then
        test_cmd="$test_cmd --timeout=$TIMEOUT"
        print_debug "Using timeout: ${TIMEOUT}s per test"
    fi
    
    # Add parallel execution
    if [ -n "$PARALLEL" ]; then
        test_cmd="$test_cmd -n $PARALLEL"
        print_debug "Running tests in parallel with $PARALLEL workers"
    fi
    
    # Handle coverage settings
    if [ "$COVERAGE_ENABLED" = false ]; then
        # Disable coverage completely (override pytest.ini defaults)
        test_cmd="$test_cmd --no-cov"
        print_debug "Coverage disabled"
    elif [ ${#TEST_ARGS[@]} -eq 0 ]; then
        # Use default coverage settings from pytest.ini for full test runs
        if [ "$CI_MODE" = true ]; then
            test_cmd="$test_cmd --cov-report=xml"
        fi
        print_debug "Using default coverage settings from pytest.ini"
    fi
    
    # Add verbosity for better output
    test_cmd="$test_cmd -v"
    
    # Add test arguments or default to all tests
    if [ ${#TEST_ARGS[@]} -gt 0 ]; then
        test_cmd="$test_cmd ${TEST_ARGS[*]}"
        print_debug "Using test arguments: ${TEST_ARGS[*]}"
    else
        test_cmd="$test_cmd tests/"
        print_debug "Testing all tests in tests/ directory"
    fi
    
    print_debug "Executing: $test_cmd"
    
    # Execute tests
    if $test_cmd; then
        print_success "Tests passed"
        return 0
    else
        local exit_code=$?
        print_error "Tests failed (exit code: $exit_code)"
        print_error "Check the test output above for specific failure details"
        return 1
    fi
}

# Validate test paths and determine target modules
validate_global_test_paths() {
    local target_modules=""
    local has_invalid_paths=false
    
    # If no TEST_ARGS with paths, return all modules
    local has_path_args=false
    for arg in "${TEST_ARGS[@]}"; do
        if [[ "$arg" == *"/"* && ! "$arg" == -* ]]; then
            has_path_args=true
            break
        fi
    done
    
    if [ "$has_path_args" = false ]; then
        echo "" # Return empty to use default modules
        return 0
    fi
    
    # Validate each path argument
    for arg in "${TEST_ARGS[@]}"; do
        if [[ "$arg" == *"/"* && ! "$arg" == -* ]]; then
            if [[ "$arg" == "src/"*"/"* ]]; then
                # Absolute path from root: src/module_name/...
                local module_name="${arg#src/}"
                module_name="${module_name%%/*}"
                if [[ "$target_modules" != *"$module_name"* ]]; then
                    target_modules="$target_modules $module_name"
                fi
            elif [[ "$arg" == "src/"* ]]; then
                # Module-level path: src/module_name (auto-expand to tests)
                local module_name="${arg#src/}"
                if [[ "$target_modules" != *"$module_name"* ]]; then
                    target_modules="$target_modules $module_name"
                fi
            elif [[ "$arg" == "./"*"/"* ]]; then
                # Relative path from src: ./module_name/...
                local module_name="${arg#./}"
                module_name="${module_name%%/*}"
                if [[ "$target_modules" != *"$module_name"* ]]; then
                    target_modules="$target_modules $module_name"
                fi
            elif [[ "$arg" == "./"* ]]; then
                # Module-level relative path: ./module_name (auto-expand to tests)
                local module_name="${arg#./}"
                if [[ "$target_modules" != *"$module_name"* ]]; then
                    target_modules="$target_modules $module_name"
                fi
            else
                print_error "Invalid test path format: '$arg'"
                print_error "Test paths must use one of these formats:"
                print_error "  ✓ src/module_name (test entire module)"
                print_error "  ✓ src/module_name/tests/... (specific path within module)"
                print_error "  ✓ ./module_name (test entire module, relative)"
                print_error "  ✓ ./module_name/tests/... (specific path, relative)"
                print_error "Examples:"
                print_error "  ✓ src/asset_core (test all asset_core tests)"
                print_error "  ✓ src/crypto_single (test all crypto_single tests)"
                print_error "  ✓ src/asset_core/tests/units/observability/test_trace_id.py"
                print_error "  ✓ src/crypto_single/tests/units/config/test_settings.py"
                print_error "  ✓ ./asset_core/tests/units/observability/test_trace_id.py"
                print_error "  ✓ ./crypto_single/tests/units"
                print_error "  ✗ /tests/units (ambiguous - which module?)"
                print_error "  ✗ test_trace_id.py (ambiguous - which module?)"
                has_invalid_paths=true
            fi
        fi
    done
    
    if [ "$has_invalid_paths" = true ]; then
        return 1
    fi
    
    echo "$target_modules" | xargs # Trim spaces
}

# Execute tests (simplified approach)
execute_tests() {
    # Process test arguments
    process_test_args
    
    # Check if we have specific test paths
    local has_test_paths=false
    for arg in "${TEST_ARGS[@]}"; do
        if [[ "$arg" == "tests/"* ]]; then
            has_test_paths=true
            break
        fi
    done
    
    if [ "$has_test_paths" = true ]; then
        print_status "Running tests with specific paths"
        # Run tests directly with the provided paths
        if ! run_tests_directly; then
            return 1
        fi
    elif [ -n "$TEST_MODULES" ]; then
        # Legacy module-based testing (for backward compatibility)
        print_status "Testing specified modules: $TEST_MODULES"
        
        local failed_modules=""
        local total_modules=0
        local passed_modules=0
        
        # Test each module using the legacy approach
        for module in $TEST_MODULES; do
            total_modules=$((total_modules + 1))
            
            print_status "[$total_modules] Testing module: $module"
            
            # Set TEST_ARGS to test the specific module
            TEST_ARGS=("tests/$module/")
            
            if run_tests_directly; then
                passed_modules=$((passed_modules + 1))
            else
                failed_modules="$failed_modules $module"
            fi
            
            echo "" # Add spacing between modules
        done
        
        # Report results
        print_status "Test Results Summary"
        echo "===================="
        echo "Total modules: $total_modules"
        echo "Passed: $passed_modules"
        echo "Failed: $((total_modules - passed_modules))"
        
        if [ -n "$failed_modules" ]; then
            print_error "Failed modules:$failed_modules"
            return 1
        else
            print_success "All modules passed!"
            return 0
        fi
    else
        # No specific paths or modules, run all tests
        print_status "Running all tests"
        if ! run_tests_directly; then
            return 1
        fi
    fi
    
    return 0
}

# Main execution
main() {
    print_status "Unified Test Engine"
    echo "=================="
    print_success "Unified Test Engine initialized"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    print_debug "Working directory: $PROJECT_ROOT"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Check prerequisites
    if ! check_uv; then
        return 1
    fi
    
    # Run quality checks if enabled
    if [ "$RUN_QUALITY_CHECKS" = true ]; then
        if ! run_quality_checks; then
            print_error "Quality checks failed"
            return 1
        fi
        print_success "Quality checks completed successfully"
    fi
    
    # Execute tests
    if ! execute_tests; then
        print_error "Test execution failed"
        return 1
    fi
    
    print_success "Test execution completed successfully"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi