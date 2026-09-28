# Makefile
VENV = .venv/Scripts
PYTHON = $(VENV)/python
PYTEST = $(VENV)/pytest

.PHONY: test run eval

# Run all unit tests
test:
	$(PYTHON) -m pytest tests/

# Run the HTTP agent service
run:
	$(PYTHON) -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Run evaluation harness (will be completed in Day 4)
eval:
	$(PYTHON) -m scripts.run_eval --cases $(or $(CASES),evals/seed_cases.jsonl)