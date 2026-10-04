# Development

## Dependencies and tests

From the repository root:

```bash
poetry install --with dev,test,docs -E all
poetry run pytest
```

Tests requiring optional engines are skipped when those engines are absent.
To run the core tests without a database:

```bash
poetry run pytest tests/test_core.py
```

Django integration tests use `config.settings_test` and require PostgreSQL
with PostGIS. The default connection is database `djangogeoexporter_test`,
user `postgres`, password `postgres`, host `localhost`, port `5432`.
Override these with `DBNAME`, `DBUSER`, `DBPASSWORD`, `DBHOST`, and `DBPORT`.
The test user must be able to create a test database with PostGIS available.

The GitHub workflow runs core tests on Python 3.12–3.14. Its integration job
installs all extras and provides a PostGIS service on Python 3.14.

## Code quality

```bash
make lint
make format
make check
poetry run pre-commit install
```

Ruff checks imports, lint rules, and formatting. The configured line length
is 79 characters.

## Building documentation

Documentation uses Markdown parsed by MyST and built with Sphinx:

```bash
poetry install --with docs
make build-docs
```

Generated pages are placed in `docs/_build/html`. For a build that fails on
warnings:

```bash
poetry run sphinx-build -n -W --keep-going -b html docs docs/_build/html
```

The Documentation workflow builds and publishes the documentation to GitHub
Pages on every push to `main`. It can also be triggered manually from the
Actions tab. In the repository settings, select **Settings > Pages > Build
and deployment > Source > GitHub Actions** to enable deployment.
