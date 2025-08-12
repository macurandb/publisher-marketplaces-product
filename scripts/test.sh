#!/bin/bash

# Test runner script for MultiMarket Hub
# Usage: ./scripts/test.sh [category] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [category] [options]"
    echo ""
    echo "Categories:"
    echo "  all           - Run all tests (default)"
    echo "  unit          - Run unit tests only (tests/apps/)"
    echo "  integration   - Run integration tests only (tests/integration/)"
    echo "  workflows     - Run workflow tests only (tests/workflows/)"
    echo "  products      - Run product app tests only"
    echo "  marketplaces  - Run marketplace app tests only"
    echo "  webhooks      - Run webhook app tests only"
    echo "  ai            - Run AI assistant tests only"
    echo "  core          - Run core app tests only"
    echo ""
    echo "Options:"
    echo "  --coverage    - Run with coverage report"
    echo "  --verbose     - Verbose output"
    echo "  --fast        - Skip slow tests"
    echo "  --parallel    - Run tests in parallel"
    echo "  --help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Run all tests"
    echo "  $0 unit --coverage          # Run unit tests with coverage"
    echo "  $0 products --verbose       # Run product tests with verbose output"
    echo "  $0 integration --fast       # Run integration tests, skip slow ones"
}

# Default values
CATEGORY="all"
COVERAGE=""
VERBOSE=""
FAST=""
PARALLEL=""
PYTEST_ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        all|unit|integration|workflows|products|marketplaces|webhooks|ai|core)
            CATEGORY="$1"
            shift
            ;;
        --coverage)
            COVERAGE="--cov=src --cov-report=html --cov-report=term"
            shift
            ;;
        --verbose)
            VERBOSE="-v"
            shift
            ;;
        --fast)
            FAST='-m "not slow"'
            shift
            ;;
        --parallel)
            PARALLEL="-n auto"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    print_color $BLUE "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set test path based on category
case $CATEGORY in
    all)
        TEST_PATH="tests/"
        print_color $BLUE "Running all tests..."
        ;;
    unit)
        TEST_PATH="tests/apps/"
        print_color $BLUE "Running unit tests..."
        ;;
    integration)
        TEST_PATH="tests/integration/"
        print_color $BLUE "Running integration tests..."
        ;;
    workflows)
        TEST_PATH="tests/workflows/"
        print_color $BLUE "Running workflow tests..."
        ;;
    products)
        TEST_PATH="tests/apps/products/"
        print_color $BLUE "Running product tests..."
        ;;
    marketplaces)
        TEST_PATH="tests/apps/marketplaces/"
        print_color $BLUE "Running marketplace tests..."
        ;;
    webhooks)
        TEST_PATH="tests/apps/webhooks/"
        print_color $BLUE "Running webhook tests..."
        ;;
    ai)
        TEST_PATH="tests/apps/ai_assistant/"
        print_color $BLUE "Running AI assistant tests..."
        ;;
    core)
        TEST_PATH="tests/apps/core/"
        print_color $BLUE "Running core tests..."
        ;;
    *)
        print_color $RED "Unknown category: $CATEGORY"
        show_usage
        exit 1
        ;;
esac

# Build pytest command
PYTEST_CMD="python -m pytest $TEST_PATH $VERBOSE $COVERAGE $FAST $PARALLEL $PYTEST_ARGS"

# Run tests
print_color $YELLOW "Command: $PYTEST_CMD"
echo ""

if eval $PYTEST_CMD; then
    print_color $GREEN "✅ Tests passed!"
    
    # Show coverage report location if coverage was run
    if [[ -n "$COVERAGE" ]]; then
        echo ""
        print_color $BLUE "📊 Coverage report generated:"
        print_color $BLUE "  - Terminal: (shown above)"
        print_color $BLUE "  - HTML: htmlcov/index.html"
    fi
else
    print_color $RED "❌ Tests failed!"
    exit 1
fi