# Makefile for MultiMarket Hub

.PHONY: install migrate run test clean

# Install dependencies
install:
	uv venv
	uv pip install -r requirements/base.txt

# Install development dependencies
install-dev:
	uv pip install -r requirements/dev.txt

# Run migrations
migrate:
	python manage.py makemigrations
	python manage.py migrate

# Create superuser
superuser:
	python manage.py createsuperuser

# Run development server
run:
	python manage.py runserver

# Run Celery worker
celery:
	celery -A src.config worker -l info

# Run tests
test:
	./scripts/test.sh all

# Run tests with coverage
test-coverage:
	./scripts/test.sh all --coverage

# Run only fast tests
test-fast:
	./scripts/test.sh all --fast

# Run integration tests
test-integration:
	./scripts/test.sh integration

# Run unit tests
test-unit:
	./scripts/test.sh unit

# Run workflow tests
test-workflows:
	./scripts/test.sh workflows

# Run tests by app
test-products:
	./scripts/test.sh products

test-marketplaces:
	./scripts/test.sh marketplaces

test-webhooks:
	./scripts/test.sh webhooks

test-ai:
	./scripts/test.sh ai

test-core:
	./scripts/test.sh core

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/

# Code Quality Commands
# ===================

# Format code with black and isort
format:
	@echo "🎨 Formatting code with black and isort..."
	black src/ tests/ --line-length 88
	isort src/ tests/ --profile black

# Check code formatting without making changes
format-check:
	@echo "🔍 Checking code formatting..."
	black src/ tests/ --check --line-length 88
	isort src/ tests/ --check-only --profile black

# Lint code with ruff
lint:
	@echo "🔍 Linting code with ruff..."
	ruff check src/ tests/

# Fix linting issues with ruff
lint-fix:
	@echo "🔧 Fixing linting issues with ruff..."
	ruff check --fix src/ tests/

# Format code with ruff
ruff-format:
	@echo "🎨 Formatting code with ruff..."
	ruff format src/ tests/

# Check ruff formatting
ruff-format-check:
	@echo "🔍 Checking ruff formatting..."
	ruff format --check src/ tests/

# Type checking with mypy
type-check:
	@echo "🔍 Type checking with mypy..."
	mypy src/ --ignore-missing-imports --no-strict-optional

# Security check with bandit
security-check:
	@echo "🔒 Running security checks with bandit..."
	@mkdir -p reports
	bandit -r src/ -f json -o reports/bandit.json || true
	@echo "🔒 Bandit scan completed (check reports/bandit.json)"

# Check for common security issues
safety-check:
	@echo "🛡️ Checking dependencies for security vulnerabilities..."
	@mkdir -p reports
	safety check --json > reports/safety.json || safety check

# Advanced security scanning with semgrep
security-scan:
	@echo "🔍 Running advanced security scan with semgrep..."
	@mkdir -p reports
	semgrep --config=.semgrep.yml --json --output=reports/semgrep.json src/ || true

# Dependency vulnerability audit with pip-audit
dependency-audit:
	@echo "🔍 Auditing dependencies with pip-audit..."
	@mkdir -p reports
	pip-audit --format=json --output=reports/pip-audit.json || true

# Generate Software Bill of Materials (SBOM)
generate-sbom:
	@echo "📋 Generating Software Bill of Materials..."
	@mkdir -p reports
	cyclonedx-py requirements requirements/base.txt -o reports/sbom.json || true

# Comprehensive security check
security-full:
	@echo "🛡️ Running comprehensive security analysis..."
	@mkdir -p reports
	$(MAKE) security-check
	$(MAKE) safety-check
	$(MAKE) security-scan
	$(MAKE) dependency-audit
	$(MAKE) generate-sbom
	@echo "🛡️ Security analysis complete! Check reports/ directory"

# Code complexity check
complexity-check:
	@echo "📊 Checking code complexity..."
	radon cc src/ -a -nc

# Check for dead code
dead-code-check:
	@echo "🧹 Checking for dead code..."
	vulture src/ --min-confidence 80

# Import sorting check
import-check:
	@echo "📦 Checking import organization..."
	isort src/ tests/ --check-only --diff --profile black

# Docstring coverage
docstring-coverage:
	@echo "📝 Checking docstring coverage..."
	docstr-coverage src/ --badge=badges --percentage-only

# Run all quality checks
quality-check: format-check lint type-check security-check complexity-check
	@echo "✅ All quality checks completed!"

# Fix all auto-fixable issues
quality-fix: format
	@echo "🔧 Auto-fixing code quality issues..."
	autopep8 --in-place --recursive src/ tests/

# Generate quality report
quality-report:
	@echo "📊 Generating code quality report..."
	@mkdir -p reports
	ruff check src/ tests/ --output-format=json > reports/ruff-report.json || true
	bandit -r src/ -f html -o reports/bandit.html || true
	radon cc src/ -a -nc --json > reports/complexity.json || true
	@echo "📊 Quality reports generated in reports/ directory"

# Check documentation links
check-links:
	@echo "🔗 Checking documentation links..."
	./scripts/check-links.sh

# Pre-commit checks (run before committing)
pre-commit: format-check lint type-check test-fast
	@echo "🚀 Pre-commit checks completed successfully!"

# CI/CD quality pipeline
ci-quality: format-check lint type-check security-check test-coverage
	@echo "🏗️ CI/CD quality pipeline completed!"

# Development setup with quality tools
setup-dev: install-dev
	@echo "🛠️ Setting up development environment with quality tools..."
	pre-commit install || echo "⚠️ pre-commit not available, skipping hook installation"

# Quality script shortcuts
quality-script-check:
	./scripts/quality.sh check

quality-script-fix:
	./scripts/quality.sh fix

quality-script-report:
	./scripts/quality.sh report

quality-script-all:
	./scripts/quality.sh all

# Help command
help:
	@echo "MultiMarket Hub - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "🏗️  Setup & Installation:"
	@echo "  install          Install base dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup-dev        Setup development environment with quality tools"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  migrate          Run database migrations"
	@echo "  superuser        Create Django superuser"
	@echo ""
	@echo "🚀 Development:"
	@echo "  run              Start development server"
	@echo "  celery           Start Celery worker"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests"
	@echo "  test-integration Run integration tests"
	@echo "  test-workflows   Run workflow tests"
	@echo "  test-coverage    Run tests with coverage"
	@echo "  test-fast        Run fast tests (skip slow ones)"
	@echo "  test-products    Run product app tests"
	@echo "  test-marketplaces Run marketplace app tests"
	@echo "  test-webhooks    Run webhook app tests"
	@echo "  test-ai          Run AI assistant tests"
	@echo "  test-core        Run core app tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  format           Format code with black and isort"
	@echo "  format-check     Check code formatting"
	@echo "  lint             Lint code with ruff"
	@echo "  lint-fix         Fix linting issues with ruff"
	@echo "  ruff-format      Format code with ruff"
	@echo "  ruff-format-check Check ruff formatting"
	@echo "  type-check       Type check with mypy"
	@echo "  security-check   Basic security check with bandit"
	@echo "  safety-check     Check dependencies for vulnerabilities"
	@echo "  security-scan    Advanced security scan with semgrep"
	@echo "  dependency-audit Audit dependencies with pip-audit"
	@echo "  generate-sbom    Generate Software Bill of Materials"
	@echo "  security-full    Comprehensive security analysis"
	@echo "  complexity-check Check code complexity"
	@echo "  dead-code-check  Check for dead code"
	@echo "  quality-check    Run all quality checks"
	@echo "  quality-fix      Auto-fix quality issues"
	@echo "  quality-report   Generate quality reports"
	@echo "  check-links      Check documentation links"
	@echo "  pre-commit       Run pre-commit checks"
	@echo "  ci-quality       Run CI/CD quality pipeline"
	@echo ""
	@echo "📊 Quality Scripts:"
	@echo "  quality-script-check   Run quality checks with script"
	@echo "  quality-script-fix     Auto-fix with script"
	@echo "  quality-script-report  Generate reports with script"
	@echo "  quality-script-all     Run all quality checks and reports"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean            Clean temporary files"
	@echo "  help             Show this help message"