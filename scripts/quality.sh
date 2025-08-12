#!/bin/bash

# Code Quality Check Script for MultiMarket Hub
# Usage: ./scripts/quality.sh [check|fix|report|all]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  check        - Run all quality checks without fixing"
    echo "  fix          - Auto-fix all fixable issues"
    echo "  report       - Generate detailed quality reports"
    echo "  format       - Format code with black and isort"
    echo "  lint         - Run linting checks"
    echo "  security     - Run basic security checks (bandit + safety)"
    echo "  security-full - Run comprehensive security analysis"
    echo "  type         - Run type checking"
    echo "  all          - Run all checks and generate reports"
    echo ""
    echo "Options:"
    echo "  --verbose - Verbose output"
    echo "  --help    - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check           # Run all quality checks"
    echo "  $0 fix             # Auto-fix formatting issues"
    echo "  $0 report          # Generate quality reports"
    echo "  $0 all --verbose   # Run everything with verbose output"
}

# Default values
COMMAND="check"
VERBOSE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        check|fix|report|format|lint|security|type|all)
            COMMAND="$1"
            shift
            ;;
        --verbose)
            VERBOSE="-v"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    print_color $BLUE "Activating virtual environment..."
    source .venv/bin/activate
fi

# Create reports directory
mkdir -p reports

# Function to run formatting
run_format() {
    print_color $BLUE "🎨 Formatting code with black and isort..."
    black src/ tests/ --line-length 88 $VERBOSE
    isort src/ tests/ --profile black $VERBOSE
    print_color $GREEN "✅ Code formatting completed!"
}

# Function to check formatting
check_format() {
    print_color $BLUE "🔍 Checking code formatting..."
    if black src/ tests/ --check --line-length 88 $VERBOSE && \
       isort src/ tests/ --check-only --profile black $VERBOSE; then
        print_color $GREEN "✅ Code formatting is correct!"
        return 0
    else
        print_color $RED "❌ Code formatting issues found!"
        return 1
    fi
}

# Function to run linting
run_lint() {
    print_color $BLUE "🔍 Linting code with ruff..."
    if ruff check src/ tests/ $VERBOSE; then
        print_color $GREEN "✅ No linting issues found!"
        return 0
    else
        print_color $RED "❌ Linting issues found!"
        return 1
    fi
}

# Function to fix linting issues
fix_lint() {
    print_color $BLUE "🔧 Fixing linting issues with ruff..."
    if ruff check --fix src/ tests/ $VERBOSE; then
        print_color $GREEN "✅ Linting issues fixed!"
        return 0
    else
        print_color $YELLOW "⚠️ Some issues couldn't be auto-fixed"
        return 1
    fi
}

# Function to run type checking
run_type_check() {
    print_color $BLUE "🔍 Type checking with mypy..."
    if mypy src/ $VERBOSE; then
        print_color $GREEN "✅ No type checking issues found!"
        return 0
    else
        print_color $YELLOW "⚠️ Type checking issues found (non-critical)"
        return 0  # Don't fail on type issues for now
    fi
}

# Function to run security checks
run_security() {
    print_color $BLUE "🔒 Running security checks..."
    mkdir -p reports
    
    # Bandit security check
    if bandit -r src/ -f json -o reports/bandit.json $VERBOSE 2>/dev/null || \
       bandit -r src/ $VERBOSE; then
        print_color $GREEN "✅ No security issues found with bandit!"
    else
        print_color $YELLOW "⚠️ Security issues found with bandit (check reports/bandit.json)"
    fi
    
    # Safety check for dependencies
    if safety check --json > reports/safety.json 2>/dev/null || \
       safety check $VERBOSE; then
        print_color $GREEN "✅ No vulnerable dependencies found!"
    else
        print_color $YELLOW "⚠️ Vulnerable dependencies found (check reports/safety.json)"
    fi
}

# Function to run advanced security scanning
run_security_advanced() {
    print_color $BLUE "🔍 Running advanced security analysis..."
    mkdir -p reports
    
    # Semgrep security scan
    if command -v semgrep >/dev/null 2>&1; then
        print_color $BLUE "Running Semgrep security scan..."
        if semgrep --config=.semgrep.yml --json --output=reports/semgrep.json src/ 2>/dev/null; then
            print_color $GREEN "✅ Semgrep scan completed!"
        else
            print_color $YELLOW "⚠️ Semgrep found potential issues (check reports/semgrep.json)"
        fi
    else
        print_color $YELLOW "⚠️ Semgrep not installed, skipping advanced scan"
    fi
    
    # Pip-audit dependency audit
    if command -v pip-audit >/dev/null 2>&1; then
        print_color $BLUE "Running pip-audit dependency scan..."
        if pip-audit --format=json --output=reports/pip-audit.json 2>/dev/null; then
            print_color $GREEN "✅ Dependency audit completed!"
        else
            print_color $YELLOW "⚠️ Dependency vulnerabilities found (check reports/pip-audit.json)"
        fi
    else
        print_color $YELLOW "⚠️ pip-audit not installed, skipping dependency audit"
    fi
    
    # Generate SBOM
    if command -v cyclonedx-py >/dev/null 2>&1; then
        print_color $BLUE "Generating Software Bill of Materials..."
        if cyclonedx-py -o reports/sbom.json 2>/dev/null; then
            print_color $GREEN "✅ Software Bill of Materials generated!"
        else
            print_color $YELLOW "⚠️ SBOM generation failed"
        fi
    else
        print_color $YELLOW "⚠️ cyclonedx-py not installed, skipping SBOM generation"
    fi
}

# Function to generate reports
generate_reports() {
    print_color $BLUE "📊 Generating quality reports..."
    
    # Flake8 HTML report
    flake8 src/ tests/ --format=html --htmldir=reports/flake8 --max-line-length=88 --extend-ignore=E203,W503 || true
    
    # Bandit HTML report
    bandit -r src/ -f html -o reports/bandit.html || true
    
    # Complexity report
    radon cc src/ -a -nc --json > reports/complexity.json || true
    radon cc src/ -a -nc > reports/complexity.txt || true
    
    # Dead code report
    vulture src/ --min-confidence 80 > reports/dead_code.txt || true
    
    # Coverage report (if .coverage exists)
    if [ -f ".coverage" ]; then
        coverage html -d reports/coverage || true
    fi
    
    print_color $GREEN "📊 Reports generated in reports/ directory!"
    print_color $BLUE "  - reports/flake8/index.html - Linting report"
    print_color $BLUE "  - reports/bandit.html - Security report"
    print_color $BLUE "  - reports/complexity.txt - Complexity analysis"
    print_color $BLUE "  - reports/dead_code.txt - Dead code analysis"
}

# Function to run all checks
run_all_checks() {
    print_color $PURPLE "🚀 Running all quality checks..."
    
    local exit_code=0
    
    check_format || exit_code=1
    run_lint || exit_code=1
    run_type_check || exit_code=1
    run_security || exit_code=1
    
    return $exit_code
}

# Main execution
case $COMMAND in
    format)
        run_format
        ;;
    lint)
        run_lint
        ;;
    security)
        run_security
        ;;
    security-full)
        run_security
        run_security_advanced
        ;;
    type)
        run_type_check
        ;;
    check)
        if run_all_checks; then
            print_color $GREEN "🎉 All quality checks passed!"
        else
            print_color $RED "❌ Some quality checks failed!"
            exit 1
        fi
        ;;
    fix)
        print_color $BLUE "🔧 Auto-fixing code quality issues..."
        run_format
        fix_lint
        autopep8 --in-place --recursive src/ tests/ || true
        print_color $GREEN "🔧 Auto-fix completed!"
        ;;
    report)
        generate_reports
        ;;
    all)
        if run_all_checks; then
            print_color $GREEN "🎉 All quality checks passed!"
        else
            print_color $YELLOW "⚠️ Some quality checks had issues"
        fi
        generate_reports
        ;;
    *)
        print_color $RED "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

print_color $GREEN "✨ Quality check process completed!"