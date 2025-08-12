#!/bin/bash

# Link Checker Script for MultiMarket Hub Documentation
# Verifies that all internal documentation links are working

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

print_color $BLUE "🔗 Checking documentation links..."

# Files to check
FILES_TO_CHECK=(
    "README.md"
    "ARCHITECTURE.md"
    "SECURITY.md"
    "tests/README.md"
    "GIT_SETUP.md"
)

# Links to verify exist
EXPECTED_FILES=(
    "ARCHITECTURE.md"
    "SECURITY.md"
    "tests/README.md"
    "GIT_SETUP.md"
    "LICENSE"
    "pyproject.toml"
    "Makefile"
    "requirements/base.txt"
    "requirements/dev.txt"
)

# Check if all expected files exist
print_color $YELLOW "Checking if referenced files exist..."
missing_files=0

for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_color $GREEN "✅ $file exists"
    else
        print_color $RED "❌ $file is missing"
        missing_files=$((missing_files + 1))
    fi
done

# Check for broken internal links in markdown files
print_color $YELLOW "Checking for broken internal links..."
broken_links=0

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        print_color $BLUE "Checking links in $file..."
        
        # Check specific known links
        if grep -q "ARCHITECTURE.md" "$file" && [ ! -f "ARCHITECTURE.md" ]; then
            print_color $RED "❌ Broken link in $file: ARCHITECTURE.md"
            broken_links=$((broken_links + 1))
        fi
        
        if grep -q "SECURITY.md" "$file" && [ ! -f "SECURITY.md" ]; then
            print_color $RED "❌ Broken link in $file: SECURITY.md"
            broken_links=$((broken_links + 1))
        fi
        
        if grep -q "tests/README.md" "$file" && [ ! -f "tests/README.md" ]; then
            print_color $RED "❌ Broken link in $file: tests/README.md"
            broken_links=$((broken_links + 1))
        fi
        
        if grep -q "GIT_SETUP.md" "$file" && [ ! -f "GIT_SETUP.md" ]; then
            print_color $RED "❌ Broken link in $file: GIT_SETUP.md"
            broken_links=$((broken_links + 1))
        fi
        
        if grep -q "LICENSE" "$file" && [ ! -f "LICENSE" ]; then
            print_color $RED "❌ Broken link in $file: LICENSE"
            broken_links=$((broken_links + 1))
        fi
        
        print_color $GREEN "✅ Links in $file are valid"
    else
        print_color $RED "❌ File $file does not exist"
        missing_files=$((missing_files + 1))
    fi
done

# Summary
print_color $BLUE "📊 Link Check Summary:"
print_color $GREEN "✅ Files checked: ${#FILES_TO_CHECK[@]}"
print_color $GREEN "✅ Expected files found: $((${#EXPECTED_FILES[@]} - missing_files))/${#EXPECTED_FILES[@]}"

if [ $missing_files -eq 0 ] && [ $broken_links -eq 0 ]; then
    print_color $GREEN "🎉 All documentation links are working correctly!"
    exit 0
else
    print_color $RED "❌ Found $missing_files missing files and $broken_links broken links"
    exit 1
fi