# Defining and serving exports

## Fields and column labels

`fields` accepts string names, `Field` objects, or a mapping of output names
to source paths. Paths such as `commune__name` traverse objects or dictionaries.
A callable source receives the current row:

```python
from djangogeoexporter import ExportTable, Field

rows = [{"id": 1, "area": 12500}]
table = ExportTable(
    "parcels",
    rows,
    (
        Field("id", label="Parcel ID"),
        Field("area_ha", source=lambda row: row["area"] / 10000,
              label="Area (ha)"),
        Field("note", default=""),
    ),
)
```

`default` is used when a string source cannot be resolved; an existing `None`
value is preserved. Explicit `Field.label` values always take precedence.
With `use_verbose_names=True`, remaining labels use the source Django field's
`verbose_name`, then fall back to the internal field name. The model is inferred
from the queryset, or supplied with `model=YourModel` for an ordinary iterable.
Duplicate output labels raise `ExportError`.

## Dynamic and relational exports

A table source can be a callable accepting the context passed to `export()`.
Override the class method `ExportDefinition.get_tables(cls, context)` when the
context also determines which tables to include.

For a relational export, declare several tables and explicitly include their
primary and foreign key columns, such as `id` and `commune_id`. The library
preserves table boundaries; it does not infer relationships or create database
foreign-key constraints. Output packaging depends on the [format](formats.md).

## JSON and JSONB

Django model `JSONField` values are detected automatically, including related
source paths. For dictionaries, computed fields, or annotations without model
metadata, declare an explicit `JSONField`:

```python
from djangogeoexporter import ExportTable, JSONField

ExportTable(
    "observations",
    [{"id": 1, "metadata": {"species": "Sérotine", "count": 2}}],
    ("id", JSONField("metadata")),
)
```

Values become compact Unicode JSON text in every format. Read them with
`json.loads(value)` or cast them with `value::jsonb` in PostgreSQL. JSON `None`
is exported as the text `null`. Non-standard numbers such as `NaN` and
`Infinity` raise `ValueError`.

## Django responses and cleanup

Use `FileResponse` to serve a generated file. Keep the temporary file available
until Django finishes streaming it. This example deletes it when the response
closes:

```python
from django.http import FileResponse

from djangogeoexporter import export
from myapp.exports import ObservationsExport


class ExportFileResponse(FileResponse):
    def __init__(self, result):
        self.export_result = result
        super().__init__(
            result.file,
            as_attachment=True,
            filename=result.filename,
            content_type=result.content_type,
        )

    def close(self):
        try:
            super().close()
        finally:
            self.export_result.cleanup()


def download_observations(request):
    # Validate filters and enforce access permissions before exporting.
    result = export(
        ObservationsExport,
        format="csv",
        context={"start_date": "2026-01-01"},
    )
    try:
        return ExportFileResponse(result)
    except Exception:
        result.cleanup()
        raise
```

For background jobs or local files, copy the result and call `cleanup()` in a
`finally` block as shown in [getting started](getting_started.md).
