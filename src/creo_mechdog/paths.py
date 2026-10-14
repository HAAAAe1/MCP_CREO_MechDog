"""Explicit source-package, distribution-resource and writable-data locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    code_root: Path
    resource_root: Path
    data_root: Path

    @classmethod
    def source_checkout(cls, root: Path, *, data_root: Path | None = None) -> ProjectPaths:
        """Describe a source installation without creating directories or reading config."""
        root = root.resolve()
        return cls(
            code_root=root / "src" / "creo_mechdog",
            resource_root=root,
            data_root=(data_root or root).resolve(),
        )

    @property
    def jobs(self) -> Path:
        return self.data_root / "jobs"

    @property
    def models(self) -> Path:
        return self.data_root / "models"

    @property
    def build(self) -> Path:
        return self.data_root / "build"


# Source installations keep resources and data beside the compatibility entries.
# Future migrations accept explicit roots instead of deriving them from moved modules.
SOURCE_PATHS = ProjectPaths.source_checkout(Path(__file__).resolve().parents[2])
