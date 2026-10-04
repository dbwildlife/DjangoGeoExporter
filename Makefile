.PHONY: lint format check pylint test build-docs graph-models docs

lint:
	poetry run ruff check djangogeoexporter config

format:
	poetry run ruff check --select I --fix djangogeoexporter config
	poetry run ruff format djangogeoexporter config

check: lint
	poetry run ruff format --check djangogeoexporter config

pylint:
	poetry run pylint --load-plugins pylint_django --django-settings-module=config.settings djangogeoexporter config

test:
	poetry run python -m manage test

build-docs:
	cd docs && poetry run make html

graph-models:
	poetry run python -m manage graph_models -g --language fr --output models.png  sinp_nomenclatures

docs: build-docs graph-models
