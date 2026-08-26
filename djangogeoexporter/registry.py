"""Writer registry used to resolve a writer from a format name."""

from __future__ import annotations

from typing import Any

from .core import ExportError


class WriterRegistry:
    """Register writer classes under one or more case-insensitive aliases."""

    def __init__(self) -> None:
        self._writers: dict[str, type] = {}

    def register(self, *names: str):
        """Decorator registering a writer class under the supplied aliases."""
        def decorator(writer_cls: type):
            for name in names:
                self._writers[name.lower()] = writer_cls
            return writer_cls

        return decorator

    def create(self, format_name: str, **options: Any):
        """Instantiate the writer registered for ``format_name``."""
        try:
            writer_cls = self._writers[format_name.lower()]
        except KeyError as exc:
            supported = ", ".join(sorted(self._writers))
            raise ExportError(f"Unsupported export format {format_name!r}. Supported: {supported}") from exc
        return writer_cls(**options)

    def formats(self) -> tuple[str, ...]:
        """Return all registered format names and aliases."""
        return tuple(sorted(self._writers))


registry = WriterRegistry()
