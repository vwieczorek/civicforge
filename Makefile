# CivicForge Development Makefile
# Simple commands for common tasks

.PHONY: help test dev install clean

help:
	@echo "CivicForge Development Commands:"
	@echo "  make install    - Set up development environment"
	@echo "  make test       - Run all tests"
	@echo "  make dev        - Start development servers"
	@echo "  make demo       - Run the prototype demo"
	@echo "  make clean      - Clean up generated files"

install:
	@echo "Setting up CivicForge development environment..."
	cd src && python -m venv venv
	cd src && ./venv/bin/pip install -r requirements-dev.txt
	@echo "✓ Backend dependencies installed"
	@echo ""
	@echo "Next steps:"
	@echo "1. Activate virtual environment: source src/venv/bin/activate"
	@echo "2. Run tests: make test"
	@echo "3. Start developing!"

test:
	@echo "Running CivicForge tests..."
	cd src && ./venv/bin/pytest core/nlp/tests/ -v
	@echo "✓ Tests complete"

dev:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: Coming soon"
	cd try-it && ./demo.sh

demo:
	@echo "Starting CivicForge demo..."
	cd try-it && ./demo.sh

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@echo "✓ Cleaned up temporary files"