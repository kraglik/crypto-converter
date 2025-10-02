.PHONY: fmt test test-cov

fmt:
	poetry run isort converter tests
	poetry run black converter

test:
	PYTHONPATH=. poetry run pytest

test-cov:
	PYTHONPATH=. poetry run pytest --cov=converter --cov-report=term-missing

