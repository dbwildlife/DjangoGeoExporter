isort:
	poetry run isort djangogeoexporter config

black:
	poetry run black djangogeoexporter config

flake8:
	poetry run flake8 djangogeoexporter config

check: isort black flake8

pylint:
	poetry run pylint --load-plugins pylint_django --django-settings-module=config.settings djangogeoexporter config

test:
	poetry run python -m manage test

build-docs:
	cd docs && poetry run make html

graph-models:
	poetry run python -m manage graph_models -g --language fr --output models.png  sinp_nomenclatures

docs: build-docs graph-models
