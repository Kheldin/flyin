.PHONY: install run debug clean lint lint-strict help

help:
	@echo "Available targets:"
	@echo "  make install      - Install project dependencies using uv"
	@echo "  make run          - Execute the main script with default paths"
	@echo "  make run MAP=<path> FUNCTIONS=<path> INPUT=<path> OUTPUT=<path>"
	@echo "                    - Run with custom file paths (MAP is required)"
	@echo "  make debug        - Run the main script in debug mode (pdb)"
	@echo "  make clean        - Remove temporary files and caches"
	@echo "  make lint         - Run flake8 and mypy with standard flags"
	@echo "  make lint-strict  - Run flake8 and mypy with strict flags"
	@echo ""
	@echo "Examples:"
	@echo "  make run MAP=maps/level1.txt"
	@echo "  make run MAP=maps/level1.txt FUNCTIONS=custom/fns.json INPUT=custom/tests.json"

install:
	@echo "Installing dependencies with uv..."
	uv sync

run:
ifndef MAP
	$(error MAP is required. Usage: make run MAP=<path/to/map.txt>)
endif
ifeq ($(suffix $(MAP)),.txt)
else
	$(error MAP must point to a .txt file. Got: '$(MAP)')
endif
	@uv run python src/main.py $(MAP)

debug:
	@echo "Running in debug mode..."
	uv run python main.py

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "Clean complete."

lint:
	@echo "Running flake8..."
	flake8 .
	@echo "Running mypy..."
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	@echo "Running flake8..."
	flake8 .
	@echo "Running mypy (strict mode)..."
	mypy . --strict