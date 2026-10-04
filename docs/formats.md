# Formats and optional dependencies

| Format | Aliases | Installation extra | Multiple tables |
| --- | --- | --- | --- |
| CSV | `csv` | None | ZIP containing one CSV per table |
| TSV | `tsv` | None | ZIP containing one TSV per table |
| Excel | `xlsx`, `excel` | `spreadsheet` | One workbook, one sheet per table |
| OpenDocument | `ods` | `spreadsheet` | One workbook, one sheet per table |
| Parquet / GeoParquet | `parquet`, `geoparquet` | `parquet` | ZIP containing one Parquet file per table |
| GeoPackage | `gpkg`, `geopackage` | `gpkg` | One GeoPackage, one layer per table |

A single CSV, TSV, or Parquet table produces a file directly. Format names are
case-insensitive. `supported_formats()` returns registered names and aliases;
it does not check whether their dependencies are installed.

```bash
pip install "djangogeoexporter[spreadsheet]"
pip install "djangogeoexporter[parquet]"
pip install "djangogeoexporter[gpkg]"
```

The `all` extra installs all engines. Spreadsheet exports use pandas with
openpyxl for XLSX and odfpy for ODS. Parquet uses pandas and PyArrow, with
GeoPandas for spatial data. GeoPackage uses pandas, GeoPandas, and Pyogrio/GDAL.
A missing required optional import raises `MissingDependencyError`. An unknown
format raises `ExportError`.

## Geometry and coordinate systems

Include the geometry column in `fields` and set `geometry_field` to its internal
name. Supply the coordinate reference system with `crs`:

```python
from djangogeoexporter import ExportDefinition, ExportTable, export


class PlacesExport(ExportDefinition):
    name = "places"
    tables = (
        ExportTable(
            "places",
            [{"id": 1, "geom": "POINT (2.35 48.86)"}],
            ("id", "geom"),
            geometry_field="geom",
            crs="EPSG:4326",
        ),
    )


result = export(PlacesExport, format="gpkg")
try:
    # Consume or copy result.path here.
    print(result.filename)
finally:
    result.cleanup()
```

Spatial writers accept Shapely geometries, GeoDjango geometries exposing WKB,
and WKT strings. The CRS describes the input coordinates; setting it does not
reproject the data. `geometry_field` is required to select spatial handling;
using a `GeometryField` marker alone does not configure it.

Parquet produces GeoParquet when a geometry field is configured. Without one,
it writes an ordinary tabular Parquet file. GeoPackage supports both spatial
and non-spatial tables.

## Writer options and memory use

Pass Parquet compression through `export(..., format="parquet",
compression="gzip")`; the default is `snappy`. GeoPackage accepts
`use_arrow=True`, which requires PyArrow in addition to the `gpkg` dependencies.

CSV and TSV use UTF-8 with a BOM and stream rows. Values exposing `wkt` are
written as WKT in these formats. Spreadsheet sheet names are truncated to
31 characters and unsupported characters are replaced with underscores.

Queryset chunking does not make every format a streaming export. Spreadsheet,
Parquet, and GeoPackage writers build DataFrames in memory; account for the
size of each table when choosing these formats.
