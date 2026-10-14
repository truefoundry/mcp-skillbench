PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: setup check reproduce-reports pilot sweep

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r eval/requirements.txt -r eval/requirements-reports.txt

check:
	$(BIN)/python -m unittest discover -s eval/tests -p 'test_*.py'
	$(BIN)/python eval/scripts/validate_bank.py --experiment linear --require-reviewed
	$(BIN)/python eval/scripts/validate_bank.py --experiment slack --require-reviewed
	$(BIN)/python eval/scripts/validate_cache.py --experiment linear
	$(BIN)/python eval/scripts/validate_cache.py --experiment slack
	$(BIN)/python eval/scripts/verify_freeze.py
	$(BIN)/python eval/scripts/scan_sensitive.py

reproduce-reports:
	$(BIN)/python eval/scripts/fetch_trajectories.py
	$(BIN)/python eval/scripts/skill_comparison.py
	$(BIN)/python eval/scripts/final_results.py

pilot:
	@test -n "$$CURSOR_API_KEY" || (echo "Set CURSOR_API_KEY before a paid pilot." && exit 1)
	$(BIN)/python eval/scripts/run_eval.py --experiment linear --pilot --attempts 1 --jobs 2 --retries 3 --run-set pilot-linear
	$(BIN)/python eval/scripts/run_eval.py --experiment slack --pilot --attempts 1 --jobs 2 --retries 3 --run-set pilot-slack

sweep:
	@test -n "$$CURSOR_API_KEY" || (echo "Set CURSOR_API_KEY before a paid sweep." && exit 1)
	@test "$$CONFIRM" = "yes" || (echo "Set CONFIRM=yes. A full sweep is a large paid run." && exit 1)
	$(BIN)/python eval/scripts/run_model_sweep.py --phase all --jobs 4 --retries 3 --skip-existing
