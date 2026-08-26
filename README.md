# DjangoGeoExporter

DjangoGeoExporter provides declarative flat, relational, and geospatial exports
from Django querysets.

## Quickstart

Install the package with the features required by your project:

```bash
poetry add "djangogeoexporter[all]"
```

Available extras are `spreadsheet` (XLSX and ODS), `parquet`, `geo`
(GeoPackage), and `all`. With pip, use the equivalent command:

```bash
pip install "djangogeoexporter[all]"
```

Declare an export using your Django models:

```python
from djangogeoexporter import ExportDefinition, ExportTable, Field

from myapp.models import Commune, Observation


class ObservationsExport(ExportDefinition):
    name = "observations"
    tables = (
        ExportTable(
            "communes",
            Commune.objects.all(),
            ("id", "name", "geom"),
            geometry_field="geom",
            crs="EPSG:4326",
        ),
        ExportTable(
            "observations",
            Observation.objects.select_related("commune"),
            (
                "id",
                Field("commune", source="commune__name"),
                "observed_at",
            ),
        ),
    )
```

Generate the export and dispose of its temporary file when finished:

```python
from shutil import copyfile

from djangogeoexporter import export

result = export(ObservationsExport, format="gpkg")
try:
    copyfile(result.path, result.filename)
finally:
    result.cleanup()
```

Supported formats include CSV, TSV, XLSX, ODS, Parquet/GeoParquet, and
GeoPackage. Relational CSV and TSV exports are returned as ZIP archives.

See the [`docs/`](docs/) directory for configuration, dynamic export contexts,
field labels, Django response integration, and format-specific options.
