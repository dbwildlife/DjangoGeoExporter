"""Core behavior tests that do not require a Django project."""

import csv
import zipfile
from dataclasses import dataclass

import pytest

from djangogeoexporter import (
    ExportDefinition,
    ExportError,
    ExportTable,
    Field,
    export,
    supported_formats,
)


@dataclass
class Commune:
    id: int
    nom: str


@dataclass
class Parcel:
    id: int
    commune: Commune
    surface: float


class FakeModelField:
    """Minimal stand-in for the Django field metadata used by the core."""

    def __init__(self, verbose_name, related_model=None):
        self.verbose_name = verbose_name
        self.related_model = related_model


class FakeMeta:
    def __init__(self, fields):
        self.fields = fields

    def get_field(self, name):
        if name not in self.fields:
            raise LookupError(name)
        return self.fields[name]


class CommuneModel:
    pass


CommuneModel._meta = FakeMeta(
    {
        "id": FakeModelField("Identifier"),
        "nom": FakeModelField("Municipality name"),
    }
)


class ParcelModel:
    pass


ParcelModel._meta = FakeMeta(
    {
        "id": FakeModelField("Identifier"),
        "commune": FakeModelField("Municipality", related_model=CommuneModel),
        "surface": FakeModelField("Cadastral area"),
    }
)


def test_flat_csv():
    rows = [Commune(1, "Paris"), Commune(2, "Lyon")]

    class Definition(ExportDefinition):
        name = "communes"
        tables = [ExportTable("communes", rows, ["id", "nom"])]

    result = export(Definition, format="csv")
    try:
        with result.path.open(encoding="utf-8-sig", newline="") as file_handle:
            data = list(csv.DictReader(file_handle))
        assert data == [
            {"id": "1", "nom": "Paris"},
            {"id": "2", "nom": "Lyon"},
        ]
    finally:
        result.cleanup()


def test_explicit_labels_are_exported():
    rows = [Parcel(10, Commune(1, "Paris"), 12_500)]

    class Definition(ExportDefinition):
        name = "parcels"
        tables = [
            ExportTable(
                "parcels",
                rows,
                [
                    Field("id", label="Parcel ID"),
                    Field("surface", label="Area (m²)"),
                ],
            )
        ]

    result = export(Definition, format="csv")
    try:
        with result.path.open(encoding="utf-8-sig", newline="") as file_handle:
            reader = csv.DictReader(file_handle)
            assert reader.fieldnames == ["Parcel ID", "Area (m²)"]
            assert next(reader) == {"Parcel ID": "10", "Area (m²)": "12500"}
    finally:
        result.cleanup()


def test_verbose_names_are_used_and_related_paths_are_traversed():
    rows = [Parcel(10, Commune(1, "Paris"), 12_500)]
    table = ExportTable(
        "parcels",
        rows,
        [
            Field("id"),
            Field("municipality_name", source="commune__nom"),
            Field("surface", label="Area override"),
            Field("computed", source=lambda row: row.surface / 10_000),
        ],
        model=ParcelModel,
        use_verbose_names=True,
    )

    # label overrides verbose_name; callable fields fall back to their internal name.
    assert table.column_labels({}) == [
        "Identifier",
        "Municipality name",
        "Area override",
        "computed",
    ]


def test_duplicate_friendly_labels_are_rejected():
    table = ExportTable(
        "parcels",
        [Parcel(10, Commune(1, "Paris"), 12_500)],
        [Field("id", label="Same"), Field("surface", label="Same")],
    )

    with pytest.raises(ExportError, match="Duplicate export column label"):
        table.column_labels({})


def test_relational_csv_is_zip():
    communes = [Commune(1, "Paris")]
    parcels = [Parcel(10, communes[0], 12_500)]

    class Definition(ExportDefinition):
        name = "cadastre"
        tables = [
            ExportTable("communes", communes, ["id", "nom"]),
            ExportTable(
                "parcels",
                parcels,
                [
                    Field("id"),
                    Field(
                        "commune_id", "commune__id", label="Municipality ID"
                    ),
                    Field(
                        "surface_ha",
                        lambda parcel: parcel.surface / 10_000,
                        label="Area (ha)",
                    ),
                ],
            ),
        ]

    result = export(Definition, format="csv")
    try:
        assert result.filename == "cadastre.zip"
        with zipfile.ZipFile(result.path) as archive:
            assert set(archive.namelist()) == {"communes.csv", "parcels.csv"}
            content = archive.read("parcels.csv").decode("utf-8-sig")
            assert "Municipality ID" in content
            assert "Area (ha)" in content
            assert "1.25" in content
    finally:
        result.cleanup()


def test_supported_formats():
    assert {"csv", "tsv", "xlsx", "ods", "parquet", "gpkg"}.issubset(
        set(supported_formats())
    )
