.PHONY: install migrate demo run lint format typecheck hooks check test browser

install:
	uv sync --locked

migrate:
	uv run python manage.py migrate

demo:
	uv run python manage.py seed_demo

run:
	uv run python manage.py runserver 127.0.0.1:8000

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

hooks:
	uv run pre-commit run --all-files --show-diff-on-failure

check: lint typecheck
	uv run python manage.py check
	uv run python manage.py makemigrations --check --dry-run

test:
	uv run pytest --cov --cov-report=term-missing --cov-report=xml

browser:
	uv run pytest -m browser
