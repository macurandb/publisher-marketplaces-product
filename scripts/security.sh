#!/bin/bash

# Security Analysis Script for MultiMarket Hub
# Usage: ./scripts/security.sh [scan-type] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Print banner
print_banner() {
    print_color $CYAN "
╔══════════════════════════════════════════════════════════════╗
║                    🛡️  SECURITY ANALYSIS                     ║
║                    MultiMarket Hub                           ║
╚══════════════════════════════════════════════════════════════╝
"
}

# Show help
show_help() {
    print_banner
    echo "Usage: $0 [scan-type] [options]"
    echo ""
    echo "Scan Types:"
    echo "  basic        - Basic security scan (bandit + safety)"
    echo "  advanced     - Advanced scan (semgrep + pip-audit)"
    echo "  full         - Comprehensive security analysis"
    echo "  sbom         - Generate Software Bill of Materials"
    echo "  report       - Generate security report"
    echo "  all          - Run all scans and generate report"
    echo ""
    echo "Options:"
    echo "  --verbose    - Verbose output"
    echo "  --fix        - Auto-fix issues where possible"
    echo "  --help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 basic              # Run basic security scan"
    echo "  $0 full --verbose     # Run comprehensive scan with verbose output"
    echo "  $0 all                # Run all scans and generate report"
}

# Parse command line arguments
COMMAND=""
VERBOSE=""
FIX=""

while [[ $# -gt 0 ]]; do
    case $1 in
        basic|advanced|full|sbom|report|all)
            COMMAND="$1"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --fix)
            FIX="--fix"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default command
if [ -z "$COMMAND" ]; then
    COMMAND="basic"
fi

# Create reports directory
mkdir -p reports

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    print_color $BLUE "Activating virtual environment..."
    source .venv/bin/activate
fi

# Basic security scan
run_basic_scan() {
    print_color $BLUE "🔒 Running basic security scan..."
    
    # Bandit static analysis
    print_color $YELLOW "Running Bandit static analysis..."
    if bandit -r src/ -f json -o reports/bandit.json $VERBOSE 2>/dev/null; then
        print_color $GREEN "✅ Bandit scan completed"
    else
        print_color $RED "❌ Bandit found security issues"
        bandit -r src/ $VERBOSE || true
    fi
    
    # Safety dependency check
    print_color $YELLOW "Checking dependencies with Safety..."
    if safety check --json > reports/safety.json 2>/dev/null; then
        print_color $GREEN "✅ No vulnerable dependencies found"
    else
        print_color $RED "❌ Vulnerable dependencies found"
        safety check $VERBOSE || true
    fi
}

# Advanced security scan
run_advanced_scan() {
    print_color $BLUE "🔍 Running advanced security scan..."
    
    # Semgrep security analysis
    if command -v semgrep >/dev/null 2>&1; then
        print_color $YELLOW "Running Semgrep security analysis..."
        if semgrep --config=.semgrep.yml --json --output=reports/semgrep.json src/ $VERBOSE 2>/dev/null; then
            print_color $GREEN "✅ Semgrep scan completed"
        else
            print_color $RED "❌ Semgrep found potential security issues"
        fi
    else
        print_color $YELLOW "⚠️ Semgrep not installed, skipping advanced scan"
        print_color $CYAN "Install with: pip install semgrep"
    fi
    
    # Pip-audit dependency audit
    if command -v pip-audit >/dev/null 2>&1; then
        print_color $YELLOW "Running pip-audit dependency audit..."
        if pip-audit --format=json --output=reports/pip-audit.json $VERBOSE 2>/dev/null; then
            print_color $GREEN "✅ Dependency audit completed"
        else
            print_color $RED "❌ Dependency vulnerabilities found"
        fi
    else
        print_color $YELLOW "⚠️ pip-audit not installed, skipping dependency audit"
        print_color $CYAN "Install with: pip install pip-audit"
    fi
}

# Generate SBOM
generate_sbom() {
    print_color $BLUE "📋 Generating Software Bill of Materials..."
    
    if command -v cyclonedx-py >/dev/null 2>&1; then
        if cyclonedx-py -o reports/sbom.json $VERBOSE 2>/dev/null; then
            print_color $GREEN "✅ SBOM generated successfully"
        else
            print_color $RED "❌ SBOM generation failed"
        fi
    else
        print_color $YELLOW "⚠️ cyclonedx-py not installed, skipping SBOM generation"
        print_color $CYAN "Install with: pip install cyclonedx-bom"
    fi
}

# Generate security report
generate_security_report() {
    print_color $BLUE "📊 Generating security report..."
    
    REPORT_FILE="reports/security-report.md"
    
    cat > "$REPORT_FILE" << EOF
# Security Analysis Report
**Generated:** $(date)
**Project:** MultiMarket Hub

## Summary

This report contains the results of comprehensive security analysis performed on the MultiMarket Hub project.

## Tools Used

- **Bandit**: Static security analysis for Python
- **Safety**: Dependency vulnerability scanner
- **Semgrep**: Advanced static analysis
- **pip-audit**: Python package vulnerability scanner
- **CycloneDX**: Software Bill of Materials generator

## Results

### Bandit Analysis
EOF

    if [ -f "reports/bandit.json" ]; then
        echo "- Report available: reports/bandit.json" >> "$REPORT_FILE"
        # Parse bandit results
        if command -v jq >/dev/null 2>&1; then
            BANDIT_ISSUES=$(jq '.results | length' reports/bandit.json 2>/dev/null || echo "0")
            echo "- Issues found: $BANDIT_ISSUES" >> "$REPORT_FILE"
        fi
    else
        echo "- No bandit report available" >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

### Safety Analysis
EOF

    if [ -f "reports/safety.json" ]; then
        echo "- Report available: reports/safety.json" >> "$REPORT_FILE"
    else
        echo "- No safety report available" >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

### Semgrep Analysis
EOF

    if [ -f "reports/semgrep.json" ]; then
        echo "- Report available: reports/semgrep.json" >> "$REPORT_FILE"
        if command -v jq >/dev/null 2>&1; then
            SEMGREP_ISSUES=$(jq '.results | length' reports/semgrep.json 2>/dev/null || echo "0")
            echo "- Issues found: $SEMGREP_ISSUES" >> "$REPORT_FILE"
        fi
    else
        echo "- No semgrep report available" >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

### Dependency Audit
EOF

    if [ -f "reports/pip-audit.json" ]; then
        echo "- Report available: reports/pip-audit.json" >> "$REPORT_FILE"
    else
        echo "- No pip-audit report available" >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

### Software Bill of Materials
EOF

    if [ -f "reports/sbom.json" ]; then
        echo "- SBOM available: reports/sbom.json" >> "$REPORT_FILE"
    else
        echo "- No SBOM available" >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

## Recommendations

1. Review all security findings in the individual reports
2. Prioritize fixing HIGH and CRITICAL severity issues
3. Update vulnerable dependencies to secure versions
4. Implement additional security controls as needed
5. Run security scans regularly as part of CI/CD pipeline

## Next Steps

- Address critical and high-severity vulnerabilities
- Update security policies and procedures
- Schedule regular security reviews
- Consider additional security tools and practices

---
*This report was generated automatically by the MultiMarket Hub security analysis script.*
EOF

    print_color $GREEN "✅ Security report generated: $REPORT_FILE"
}

# Main execution
print_banner

case $COMMAND in
    basic)
        run_basic_scan
        ;;
    advanced)
        run_advanced_scan
        ;;
    full)
        run_basic_scan
        run_advanced_scan
        ;;
    sbom)
        generate_sbom
        ;;
    report)
        generate_security_report
        ;;
    all)
        run_basic_scan
        run_advanced_scan
        generate_sbom
        generate_security_report
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

print_color $GREEN "🛡️ Security analysis completed!"
print_color $CYAN "Check the reports/ directory for detailed results."