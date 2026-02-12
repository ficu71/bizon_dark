from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.codec.contracts import ParsedSaveFile


class SaveCodec(ABC):
    """Common interface for every persist.* codec."""

    @abstractmethod
    def supports(self, file_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedSaveFile:
        raise NotImplementedError

    @abstractmethod
    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        raise NotImplementedError
