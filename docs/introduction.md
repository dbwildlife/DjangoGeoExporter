# Introduction

DjangoGeoExporter describes exports through three main objects:

- `ExportDefinition` groups the tables and defines the output filename stem.
- `ExportTable` selects a queryset or iterable, its fields, and optional geometry.
- `Field` maps a source value to an output column, with an optional label.

The `export()` function selects a writer and returns an `ExportResult` containing
the temporary file path, suggested filename, and content type.

CSV and TSV work without optional dependencies. Spreadsheet and geospatial
formats use optional engines installed through package extras. See
[formats](formats.md) for dependencies and the behavior of multiple tables.

The core does not import Django and can export dictionaries or Python objects.
In a Django application, it accepts querysets and reads model metadata for
JSON fields and optional human-friendly column names. The library does not
provide API endpoints, models, migrations, or a required `INSTALLED_APPS` entry.
Views, access checks, and queryset filtering belong to the application using it.

Python 3.12 or later is required (below Python 4). The CI unit tests run on
Python 3.12, 3.13, and 3.14. Django is supplied by the consuming application;
the repository's development and test dependencies specify Django 4 or later.
