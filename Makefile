.PHONY: fmt test test-cov lint typecheck check

fmt:
	poetry run ruff check . --select I --fix
	poetry run ruff check . --fix
	poetry run ruff format .

lint:
	poetry run ruff check converter

test:
	PYTHONPATH=. poetry run pytest

test-cov:
	PYTHONPATH=. poetry run pytest --cov=converter --cov-report=term-missing

typecheck:
	poetry run mypy --package converter

check: fmt lint typecheck test
