"""Core data structures used to describe and materialize exports.

The core intentionally avoids importing Django. Django models and QuerySets are
handled by duck typing so the package remains usable and testable without a
Django runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence


MISSING = object()


@dataclass(frozen=True)
class Field:
    """Describe one logical export field.

    Args:
        name: Stable internal name used by the export definition.
        source: Attribute/path used to read the value, or a callable receiving
            the source object. Django-style ``__`` paths are supported.
        default: Value returned when a string source cannot be resolved.
        label: Optional human-friendly column name. It has precedence over a
            Django model field's ``verbose_name``.
    """

    name: str
    source: str | Callable[[Any], Any] | None = None
    default: Any = None
    label: str | None = None

    def resolve(self, row: Any) -> Any:
        """Resolve this field's value from a source row/object."""
        source = self.source if self.source is not None else self.name
        if callable(source):
            return source(row)
        value = resolve_path(row, source, MISSING)
        return self.default if value is MISSING else value


@dataclass(frozen=True)
class GeometryField(Field):
    """Marker field for a geometry column.

    Geometry values are handled like regular fields until a spatial writer
    converts them to Shapely/GeoPandas objects.
    """


@dataclass(frozen=True)
class JSONField(Field):
    """Marker for a field whose value must be exported as JSON text.

    Use this class for dictionaries, lists and JSON scalar values coming from
    plain Python iterables. Django model ``JSONField`` columns are detected
    automatically, so they do not need to be declared explicitly.
    """


@dataclass
class ExportTable:
    """Describe one table/layer of an export.

    ``use_verbose_names`` is opt-in. When enabled, output column names are
    resolved in this order:

    1. ``Field.label`` when explicitly provided.
    2. Django's ``verbose_name`` for the source field, when resolvable.
    3. The stable internal ``Field.name``.

    For related paths such as ``commune__name``, verbose-name resolution walks
    the model relationship and uses the terminal field's ``verbose_name``.

    Args:
        name: Table name, spreadsheet sheet name, archive member prefix or
            GeoPackage layer name depending on the writer.
        queryset: Iterable of objects/rows, or a callable receiving export
            context and returning one.
        fields: Sequence of ``Field`` objects/string names, or a mapping of
            internal output names to source paths.
        model: Optional Django model class used for ``verbose_name`` lookup.
            Usually unnecessary because it can be inferred from a QuerySet.
            Supplying it is useful when ``queryset`` is a plain iterable.
        use_verbose_names: Use Django ``verbose_name`` values as fallback
            human-friendly output labels.
        geometry_field: Internal field name containing geometry data.
        crs: Coordinate reference system passed to GeoPandas.
        chunk_size: Chunk size used when a source provides ``iterator()``.
    """

    name: str
    queryset: Iterable[Any] | Callable[[Mapping[str, Any]], Iterable[Any]]
    fields: Sequence[Field | str] | Mapping[str, str]
    model: type | None = None
    use_verbose_names: bool = False
    geometry_field: str | None = None
    crs: str | None = None
    chunk_size: int = 2000

    def normalized_fields(self) -> list[Field]:
        """Return all configured fields as ``Field`` instances."""
        if isinstance(self.fields, Mapping):
            return [
                GeometryField(name, source) if name == self.geometry_field else Field(name, source)
                for name, source in self.fields.items()
            ]

        result: list[Field] = []
        for item in self.fields:
            if isinstance(item, Field):
                result.append(item)
            else:
                cls = GeometryField if item == self.geometry_field else Field
                result.append(cls(item))
        return result

    def source(self, context: Mapping[str, Any]) -> Iterable[Any]:
        """Resolve the configured iterable/QuerySet for an export context."""
        return self.queryset(context) if callable(self.queryset) else self.queryset

    def resolve_model(self, context: Mapping[str, Any]) -> type | None:
        """Return the Django model used for metadata lookup when available.

        The explicitly configured ``model`` takes precedence. Otherwise a
        QuerySet-like source's ``model`` attribute is used. No Django import is
        required.
        """
        if self.model is not None:
            return self.model
        return getattr(self.source(context), "model", None)

    def column_labels(self, context: Mapping[str, Any]) -> list[str]:
        """Return final user-facing output column names.

        Duplicate labels are rejected because writers such as CSV and pandas
        DataFrames cannot reliably preserve a one-to-one mapping otherwise.
        """
        model = self.resolve_model(context) if self.use_verbose_names else None
        labels = [self._field_label(field, model) for field in self.normalized_fields()]
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            joined = ", ".join(repr(label) for label in duplicates)
            raise ExportError(f"Duplicate export column label(s) in table {self.name!r}: {joined}")
        return labels

    def geometry_label(self, context: Mapping[str, Any]) -> str | None:
        """Return the final exported name of the configured geometry field."""
        if self.geometry_field is None:
            return None
        fields = self.normalized_fields()
        labels = self.column_labels(context)
        for export_field, label in zip(fields, labels):
            if export_field.name == self.geometry_field:
                return label
        return self.geometry_field

    def rows(self, context: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        """Yield rows keyed by stable internal field names.

        This method intentionally keeps internal names. Writers should normally
        consume ``export_rows`` instead, which replaces keys with friendly
        labels.
        """
        source = self.source(context)
        # Django QuerySet supports iterator(); ordinary iterables do not.
        if hasattr(source, "iterator"):
            source = source.iterator(chunk_size=self.chunk_size)
        fields = self.normalized_fields()
        for item in source:
            yield {column.name: column.resolve(item) for column in fields}

    def export_rows(self, context: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        """Yield rows keyed by their final user-facing column labels."""
        fields = self.normalized_fields()
        labels = self.column_labels(context)
        model = self.resolve_model(context)
        for row in self.rows(context):
            yield {
                label: serialize_json(row[field.name])
                if self._is_json_field(field, model)
                else row[field.name]
                for field, label in zip(fields, labels)
            }

    @staticmethod
    def _is_json_field(export_field: Field, model: type | None) -> bool:
        """Return whether a configured field represents Django JSON data."""
        if isinstance(export_field, JSONField):
            return True
        source = (
            export_field.source
            if export_field.source is not None
            else export_field.name
        )
        if model is None or not isinstance(source, str):
            return False
        model_field = resolve_model_field(model, source)
        if model_field is None:
            return False
        get_internal_type = getattr(model_field, "get_internal_type", None)
        return callable(get_internal_type) and get_internal_type() == "JSONField"

    def _field_label(self, export_field: Field, model: type | None) -> str:
        """Resolve a field label according to the documented precedence."""
        if export_field.label is not None:
            return str(export_field.label)

        if model is not None:
            source = export_field.source if export_field.source is not None else export_field.name
            if isinstance(source, str):
                verbose_name = resolve_verbose_name(model, source)
                if verbose_name:
                    return verbose_name

        return export_field.name


class ExportDefinition:
    """Base class for declarative exports.

    Subclasses usually only provide a ``name`` and a sequence of ``tables``.
    ``get_tables`` can be overridden for context-dependent definitions.
    """

    name = "export"
    tables: Sequence[ExportTable] = ()

    @classmethod
    def get_tables(cls, context: Mapping[str, Any]) -> Sequence[ExportTable]:
        """Return tables to export for the current context."""
        return cls.tables


@dataclass
class ExportResult:
    """Metadata and filesystem handle for a generated export."""

    path: Path
    filename: str
    content_type: str

    @property
    def file(self):
        """Open the generated file in binary read mode."""
        return self.path.open("rb")

    def cleanup(self) -> None:
        """Delete the temporary export file if it still exists."""
        self.path.unlink(missing_ok=True)


class ExportError(RuntimeError):
    """Base exception raised by the export package."""


class MissingDependencyError(ExportError):
    """Raised when a writer's optional dependency is not installed."""


def resolve_path(obj: Any, path: str, default: Any = None) -> Any:
    """Resolve a Django-style ``foo__bar`` path on objects or mappings."""
    current = obj
    for part in path.split("__"):
        if current is None:
            return default
        if isinstance(current, Mapping):
            current = current.get(part, MISSING)
        else:
            current = getattr(current, part, MISSING)
        if current is MISSING:
            return default
        if callable(current) and not isinstance(current, type):
            try:
                current = current()
            except TypeError:
                # Some callable attributes require arguments and should simply
                # be returned as-is rather than invoked.
                pass
    return current


def resolve_verbose_name(model: type, source_path: str) -> str | None:
    """Resolve Django ``verbose_name`` metadata for a source path.

    The function deliberately uses Django's public model metadata interface via
    duck typing instead of importing Django. Related paths are traversed through
    each field's ``related_model`` attribute.

    Returns ``None`` when the path is not backed by Django model fields (for
    example an annotation, property or arbitrary computed attribute).
    """
    current_model: type | None = model
    parts = source_path.split("__")

    for index, part in enumerate(parts):
        model_meta = getattr(current_model, "_meta", None)
        if model_meta is None or not hasattr(model_meta, "get_field"):
            return None

        try:
            model_field = model_meta.get_field(part)
        except Exception:
            # Django raises FieldDoesNotExist here; keeping the core free of a
            # Django import also lets non-Django metadata objects participate.
            return None

        if index == len(parts) - 1:
            verbose_name = getattr(model_field, "verbose_name", None)
            return str(verbose_name) if verbose_name is not None else None

        current_model = getattr(model_field, "related_model", None)
        if current_model is None:
            return None

    return None


def resolve_model_field(model: type, source_path: str) -> Any | None:
    """Resolve the terminal Django model field for a ``__`` source path."""
    current_model: type | None = model
    parts = source_path.split("__")
    for index, part in enumerate(parts):
        model_meta = getattr(current_model, "_meta", None)
        if model_meta is None or not hasattr(model_meta, "get_field"):
            return None
        try:
            model_field = model_meta.get_field(part)
        except Exception:
            return None
        if index == len(parts) - 1:
            return model_field
        current_model = getattr(model_field, "related_model", None)
        if current_model is None:
            return None
    return None


def serialize_json(value: Any) -> str:
    """Return strict UTF-8 JSON accepted by Python and PostgreSQL.

    ``allow_nan=False`` is intentional: PostgreSQL JSON rejects the JavaScript
    spellings ``NaN`` and ``Infinity`` even though Python's encoder otherwise
    emits them by default.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def temp_path(suffix: str) -> Path:
    """Create and return a closed temporary path with the requested suffix."""
    file_handle = NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(file_handle.name)
    file_handle.close()
    return path
