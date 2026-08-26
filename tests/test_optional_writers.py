from dataclasses import dataclass

import pytest

from djangogeoexporter import ExportDefinition, ExportTable, export


@dataclass
class Row:
    id: int
    name: str
    geom: object = None


def definition(fields=("id", "name"), *, geometry_field=None):
    class Definition(ExportDefinition):
        name = "sample"
        tables = [
            ExportTable(
                "rows",
                [Row(1, "first")],
                fields,
                geometry_field=geometry_field,
                crs="EPSG:4326" if geometry_field else None,
            )
        ]

    return Definition


@pytest.mark.parametrize(
    ("export_format", "expected_suffix"),
    (("xlsx", ".xlsx"), ("ods", ".ods"), ("parquet", ".parquet")),
)
def test_tabular_optional_writers(export_format, expected_suffix):
    result = export(definition(), format=export_format)
    try:
        assert result.path.suffix == expected_suffix
        assert result.path.stat().st_size > 0
    finally:
        result.cleanup()


def test_geopackage_writer_preserves_geometry():
    shapely = pytest.importorskip("shapely.geometry")
    pyogrio = pytest.importorskip("pyogrio")

    export_definition = definition(
        ("id", "name", "geom"), geometry_field="geom"
    )
    export_definition.tables[0].queryset = [
        Row(1, "Paris", shapely.Point(2.35, 48.86))
    ]

    result = export(export_definition, format="gpkg")
    try:
        assert pyogrio.list_layers(result.path).tolist() == [["rows", "Point"]]
    finally:
        result.cleanup()
