# Getting started

## Installation

For CSV and TSV only:

```bash
pip install djangogeoexporter
```

For all supported formats:

```bash
pip install "djangogeoexporter[all]"
```

With Poetry, use `poetry add "djangogeoexporter[all]"`. You can select the
`spreadsheet`, `parquet`, or `gpkg` extra instead of `all`.

## A first export

This example runs without Django or a database:

```python
from shutil import copyfile

from djangogeoexporter import ExportDefinition, ExportTable, export


class CommunesExport(ExportDefinition):
    name = "communes"
    tables = (
        ExportTable(
            "communes",
            [{"id": 1, "name": "Paris"}, {"id": 2, "name": "Lyon"}],
            ("id", "name"),
        ),
    )


result = export(CommunesExport, format="csv")
try:
    copyfile(result.path, result.filename)
finally:
    result.cleanup()
```

The result is copied to `communes.csv` in the current directory. `result.path`
is a temporary file, so call `cleanup()` after consuming or copying it.
`result.file` opens a new binary stream; the caller must close that stream.

## Django querysets

For a model in your application, replace the iterable with a queryset:

```python
from djangogeoexporter import ExportDefinition, ExportTable, Field
from myapp.models import Observation


class ObservationsExport(ExportDefinition):
    name = "observations"
    tables = (
        ExportTable(
            "observations",
            lambda context: Observation.objects.filter(
                observed_at__gte=context["start_date"]
            ).select_related("commune"),
            (
                "id",
                Field("commune_name", source="commune__name"),
                "observed_at",
            ),
        ),
    )
```

Pass the required values with
`export(ObservationsExport, format="csv", context={"start_date": "2026-01-01"})`.
The model and field names in this example must match your application.
Querysets are consumed through `iterator()` with a default chunk size of 2000.
