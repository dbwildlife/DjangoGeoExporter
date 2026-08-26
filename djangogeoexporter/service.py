"""Public service functions for generating exports."""

from __future__ import annotations

from typing import Any, Mapping

from .core import ExportDefinition, ExportResult
from .registry import registry
# Importing built-in writers registers them in the global writer registry.
from . import writers as _writers  # noqa: F401


def export(
    definition: type[ExportDefinition],
    *,
    format: str,
    context: Mapping[str, Any] | None = None,
    **writer_options: Any,
) -> ExportResult:
    """Generate an export using a declarative ``ExportDefinition``.

    Args:
        definition: Export definition class.
        format: Registered output format such as ``csv``, ``xlsx`` or ``gpkg``.
        context: Arbitrary values consumed by table queryset callables.
        **writer_options: Format-specific options forwarded to the writer.

    Returns:
        An ``ExportResult`` pointing to the generated temporary file.
    """
    writer = registry.create(format, **writer_options)
    return writer.write(definition, context or {})


def supported_formats() -> tuple[str, ...]:
    """Return all currently registered format names and aliases."""
    return registry.formats()
