"""Built-in writers for tabular and geospatial export formats."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any, Mapping

from .core import ExportDefinition, ExportResult, ExportTable, MissingDependencyError, temp_path
from .registry import registry


class BaseWriter:
    """Base interface implemented by every export writer."""

    extension = "bin"
    content_type = "application/octet-stream"

    def __init__(self, **options: Any) -> None:
        self.options = options

    def write(self, definition: type[ExportDefinition], context: Mapping[str, Any]) -> ExportResult:
        """Write an export and return its generated file metadata."""
        raise NotImplementedError

    def result(
        self,
        definition: type[ExportDefinition],
        path: Path,
        *,
        extension: str | None = None,
        content_type: str | None = None,
    ) -> ExportResult:
        """Build a standard ``ExportResult`` for a writer output."""
        ext = extension or self.extension
        return ExportResult(path, f"{definition.name}.{ext}", content_type or self.content_type)


class DelimitedWriter(BaseWriter):
    """Shared implementation for CSV and TSV outputs."""

    delimiter = ","
    extension = "csv"
    content_type = "text/csv"

    def write(self, definition: type[ExportDefinition], context: Mapping[str, Any]) -> ExportResult:
        tables = list(definition.get_tables(context))
        if len(tables) == 1:
            path = temp_path(f".{self.extension}")
            self._write_table(path, tables[0], context)
            return self.result(definition, path)

        # Relational delimited exports are represented as one file per table in
        # a ZIP archive, preserving table boundaries and foreign-key columns.
        path = temp_path(".zip")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for table in tables:
                buffer = io.StringIO(newline="")
                self._write_table_stream(buffer, table, context)
                archive.writestr(f"{table.name}.{self.extension}", buffer.getvalue())
        return self.result(definition, path, extension="zip", content_type="application/zip")

    def _write_table(self, path: Path, table: ExportTable, context: Mapping[str, Any]) -> None:
        # UTF-8 with BOM remains convenient for direct opening in desktop Excel.
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            self._write_table_stream(stream, table, context)

    def _write_table_stream(self, stream, table: ExportTable, context: Mapping[str, Any]) -> None:
        columns = table.column_labels(context)
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
            delimiter=self.delimiter,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in table.export_rows(context):
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


@registry.register("csv")
class CsvWriter(DelimitedWriter):
    """Comma-separated values writer."""


@registry.register("tsv")
class TsvWriter(DelimitedWriter):
    """Tab-separated values writer."""

    delimiter = "\t"
    extension = "tsv"
    content_type = "text/tab-separated-values"


class SpreadsheetWriter(BaseWriter):
    """Shared pandas-based implementation for XLSX and ODS workbooks."""

    engine = "openpyxl"
    extension = "xlsx"
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def write(self, definition: type[ExportDefinition], context: Mapping[str, Any]) -> ExportResult:
        try:
            import pandas as pd
        except ImportError as exc:
            raise MissingDependencyError("Spreadsheet exports require pandas") from exc

        path = temp_path(f".{self.extension}")
        try:
            with pd.ExcelWriter(path, engine=self.engine) as excel:
                for table in definition.get_tables(context):
                    columns = table.column_labels(context)
                    dataframe = pd.DataFrame(table.export_rows(context), columns=columns)
                    dataframe.to_excel(excel, sheet_name=_sheet_name(table.name), index=False)
        except ImportError as exc:
            raise MissingDependencyError(
                f"{self.extension} export requires the optional engine {self.engine!r}"
            ) from exc
        return self.result(definition, path)


@registry.register("xlsx", "excel")
class XlsxWriter(SpreadsheetWriter):
    """Microsoft Excel XLSX writer using openpyxl through pandas."""


@registry.register("ods")
class OdsWriter(SpreadsheetWriter):
    """OpenDocument Spreadsheet writer using odfpy through pandas."""

    engine = "odf"
    extension = "ods"
    content_type = "application/vnd.oasis.opendocument.spreadsheet"


@registry.register("parquet", "geoparquet")
class ParquetWriter(BaseWriter):
    """Parquet/GeoParquet writer.

    Multiple logical tables are returned as a ZIP containing one Parquet file
    per table.
    """

    extension = "parquet"
    content_type = "application/vnd.apache.parquet"

    def write(self, definition: type[ExportDefinition], context: Mapping[str, Any]) -> ExportResult:
        tables = list(definition.get_tables(context))
        if len(tables) == 1:
            path = temp_path(".parquet")
            self._write_table(path, tables[0], context)
            return self.result(definition, path)

        zip_path = temp_path(".zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for table in tables:
                part = temp_path(".parquet")
                try:
                    self._write_table(part, table, context)
                    archive.write(part, arcname=f"{table.name}.parquet")
                finally:
                    part.unlink(missing_ok=True)
        return self.result(definition, zip_path, extension="zip", content_type="application/zip")

    def _write_table(self, path: Path, table: ExportTable, context: Mapping[str, Any]) -> None:
        try:
            import pandas as pd
            import pyarrow  # noqa: F401  # Ensures pandas has a Parquet engine.
        except ImportError as exc:
            raise MissingDependencyError("Parquet exports require pandas and pyarrow") from exc

        rows = list(table.export_rows(context))
        if table.geometry_field:
            geodataframe = _geodataframe(rows, table, context)
            geodataframe.to_parquet(
                path,
                index=False,
                compression=self.options.get("compression", "snappy"),
            )
        else:
            pd.DataFrame(rows, columns=table.column_labels(context)).to_parquet(
                path,
                index=False,
                compression=self.options.get("compression", "snappy"),
            )


@registry.register("gpkg", "geopackage")
class GeoPackageWriter(BaseWriter):
    """GeoPackage writer using Pyogrio.

    Each ``ExportTable`` becomes one GeoPackage layer/table. Spatial tables are
    written as GeoDataFrames and non-spatial tables as ordinary DataFrames.
    """

    extension = "gpkg"
    content_type = "application/geopackage+sqlite3"

    def write(self, definition: type[ExportDefinition], context: Mapping[str, Any]) -> ExportResult:
        try:
            from pyogrio import write_dataframe
        except ImportError as exc:
            raise MissingDependencyError("GeoPackage exports require geopandas and pyogrio") from exc

        path = temp_path(".gpkg")
        # NamedTemporaryFile created an empty file; GDAL expects to create the
        # datasource itself on the first write.
        path.unlink(missing_ok=True)

        for table in definition.get_tables(context):
            rows = list(table.export_rows(context))
            frame = (
                _geodataframe(rows, table, context)
                if table.geometry_field
                else _dataframe(rows, table, context)
            )
            write_dataframe(
                frame,
                path,
                layer=table.name,
                driver="GPKG",
                # Pyogrio/GDAL can add another layer to an existing GPKG.
                append=path.exists(),
                use_arrow=bool(self.options.get("use_arrow", False)),
            )
        return self.result(definition, path)


def _dataframe(rows: list[dict[str, Any]], table: ExportTable, context: Mapping[str, Any]):
    """Create a pandas DataFrame with final friendly column labels."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise MissingDependencyError("This export requires pandas") from exc
    return pd.DataFrame(rows, columns=table.column_labels(context))


def _geodataframe(
    rows: list[dict[str, Any]],
    table: ExportTable,
    context: Mapping[str, Any],
):
    """Create a GeoDataFrame and normalize common geometry representations."""
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise MissingDependencyError("Spatial exports require geopandas") from exc

    frame = _dataframe(rows, table, context)
    geometry_column = table.geometry_label(context)
    if geometry_column is None:
        return frame
    if geometry_column not in frame.columns:
        raise ValueError(f"Geometry column {geometry_column!r} is missing from table {table.name!r}")
    frame[geometry_column] = frame[geometry_column].map(_to_shapely)
    return gpd.GeoDataFrame(frame, geometry=geometry_column, crs=table.crs)


def _to_shapely(value: Any) -> Any:
    """Convert GeoDjango/WKT geometry values to Shapely when necessary."""
    if value is None:
        return None

    # Shapely geometry objects can be used as-is.
    if hasattr(value, "geom_type") and value.__class__.__module__.startswith("shapely"):
        return value

    # GeoDjango GEOSGeometry exposes ``wkb``.
    if hasattr(value, "wkb"):
        try:
            from shapely import wkb

            return wkb.loads(bytes(value.wkb))
        except Exception:
            pass

    # WKT is a convenient fallback for user-provided rows.
    if isinstance(value, str):
        try:
            from shapely import wkt

            return wkt.loads(value)
        except Exception:
            return value
    return value


def _csv_value(value: Any) -> Any:
    """Convert values requiring a simple textual representation for CSV/TSV."""
    if value is None:
        return ""
    if hasattr(value, "wkt"):
        try:
            return value.wkt
        except Exception:
            pass
    return value


def _sheet_name(name: str) -> str:
    """Return an Excel-compatible sheet name (maximum 31 characters)."""
    forbidden = set('[]:*?/\\')
    cleaned = "".join("_" if char in forbidden else char for char in name)
    return cleaned[:31] or "Sheet1"
