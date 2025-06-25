#!/bin/bash

# Module Detection Script
# Detects which modules are ready for testing
# A module is ready if:
# 1. Has pyproject.toml
# 2. Has tests/ directory
# 3. Has at least one test_*.py file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${BLUE}🔍 DEBUG: $1${NC}" >&2
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

print_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Check if a module is ready for testing
is_module_ready() {
    local module_path="$1"
    local module_name=$(basename "$module_path")
    
    print_debug "Checking module: $module_name at $module_path"
    
    # Check if pyproject.toml exists
    if [ ! -f "$module_path/pyproject.toml" ]; then
        print_debug "$module_name: No pyproject.toml found"
        return 1
    fi
    
    # Check if tests directory exists
    if [ ! -d "$module_path/tests" ]; then
        print_debug "$module_name: No tests directory found"
        return 1
    fi
    
    # Check if there are any test files
    local test_files=$(find "$module_path/tests" -name "test_*.py" 2>/dev/null | wc -l)
    if [ "$test_files" -eq 0 ]; then
        print_debug "$module_name: No test files found"
        return 1
    fi
    
    print_debug "$module_name: Module is ready (has $test_files test files)"
    return 0
}

# Detect all ready modules
detect_ready_modules() {
    local src_dir="${1:-src}"
    local ready_modules=()
    
    if [ ! -d "$src_dir" ]; then
        print_error "Source directory '$src_dir' not found"
        return 1
    fi
    
    print_debug "Scanning for modules in $src_dir"
    
    # Scan each directory in src/
    for module_path in "$src_dir"/*; do
        if [ -d "$module_path" ]; then
            local module_name=$(basename "$module_path")
            
            # Skip hidden directories and __pycache__
            if [[ "$module_name" == .* ]] || [[ "$module_name" == "__pycache__" ]]; then
                continue
            fi
            
            if is_module_ready "$module_path"; then
                ready_modules+=("$module_name")
                print_info "✅ Module ready: $module_name"
            else
                print_warning "⏳ Module not ready: $module_name"
            fi
        fi
    done
    
    # Output ready modules (space-separated)
    if [ ${#ready_modules[@]} -gt 0 ]; then
        echo "${ready_modules[*]}"
        return 0
    else
        print_error "No modules ready for testing"
        return 1
    fi
}

# Main function
main() {
    local src_dir="src"
    local show_help=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --src-dir)
                src_dir="$2"
                shift 2
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help|-h)
                show_help=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help=true
                shift
                ;;
        esac
    done
    
    if [ "$show_help" = true ]; then
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --src-dir DIR    Source directory to scan (default: src)"
        echo "  --debug          Enable debug output"
        echo "  --help, -h       Show this help message"
        echo ""
        echo "Output:"
        echo "  Space-separated list of ready module names"
        echo ""
        echo "Exit codes:"
        echo "  0  - Modules found"
        echo "  1  - No modules found or error"
        return 0
    fi
    
    detect_ready_modules "$src_dir"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi