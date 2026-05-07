"""File validation service — allowlist, MIME check, size limits, quarantine.

Regla 14 de AGENTS.md: "Allowlist de tipo, validacion MIME, limites de tamano, cuarentena.
Marcar como [PARTIAL]/[TARGET] si no cumple."
"""

import logging
import mimetypes
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)


class FileStatus(Enum):
    ALLOWED = "allowed"
    QUARANTINE = "quarantine"
    REJECTED = "rejected"


@dataclass
class ValidationResult:
    """Resultado de validacion de fichero."""

    status: FileStatus = FileStatus.REJECTED
    allowed_extensions: set[str] = field(default_factory=set)
    allowed_mimes: set[str] = field(default_factory=set)
    max_size: int = 0
    file_size: int = 0
    detected_mime: str = ""
    detected_extension: str = ""
    rejection_reason: str = ""

    @property
    def is_allowed(self) -> bool:
        return self.status == FileStatus.ALLOWED

    @property
    def is_quarantined(self) -> bool:
        return self.status == FileStatus.QUARANTINE


# ---------------------------------------------------------------------------
# Configuracion por tipo de fichero
# ---------------------------------------------------------------------------

# Maximo 50MB por defecto
DEFAULT_MAX_SIZE: Final = 50 * 1024 * 1024

# Allowlist MIME por familia
ALLOWED_MIME_FAMILIES: Final = {
    "xml": {"application/xml", "text/xml"},
    "csv": {"text/csv", "text/plain", "application/csv", "application/vnd.ms-excel"},
    "json": {"application/json"},
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    },
}

# Extensiones permitidas por familia
ALLOWED_EXTENSIONS: Final = {
    "xml": {".xml"},
    "csv": {".csv"},
    "json": {".json"},
    "pdf": {".pdf"},
    "txt": {".txt", ".n43"},
    "xlsx": {".xlsx", ".xls"},
}

# Mapeo MIME -> familia permitida
MIME_TO_FAMILY: Final[dict[str, str]] = {}
for family, mimes in ALLOWED_MIME_FAMILIES.items():
    for mime in mimes:
        MIME_TO_FAMILY[mime] = family

# Extensiones permitidas planas (sin familia)
ALL_ALLOWED_EXTS: Final[set[str]] = set()
for exts in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTS.update(exts)


class FileValidator:
    """Valida ficheros uploads: allowlist extension, MIME, tamano, cuarentena."""

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        strict_mime: bool = True,
        quarantine_dir: str | None = None,
    ):
        self.max_size = max_size
        self.strict_mime = strict_mime
        self.quarantine_dir = Path(quarantine_dir) if quarantine_dir else None
        if self.quarantine_dir:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def validate(
        self,
        filename: str,
        content: bytes,
        allowed_types: list[str] | None = None,
    ) -> ValidationResult:
        """Valida un fichero contra la allowlist.

        Args:
            filename: Nombre original del fichero.
            content: Contenido binario del fichero.
            allowed_types: Lista de familias permitidas (xml, csv, json, pdf, txt, xlsx).
                          Si es None, usa todas las permitidas.

        Returns:
            ValidationResult con el estado del fichero.
        """
        allowed_types = allowed_types or list(ALLOWED_EXTENSIONS.keys())
        allowed_exts: set[str] = set()
        allowed_mimes: set[str] = set()
        for family in allowed_types:
            allowed_exts.update(ALLOWED_EXTENSIONS.get(family, set()))
            allowed_mimes.update(ALLOWED_MIME_FAMILIES.get(family, set()))

        result = ValidationResult(
            allowed_extensions=allowed_exts,
            allowed_mimes=allowed_mimes,
            max_size=self.max_size,
            file_size=len(content),
        )

        # 1. Check size
        if len(content) == 0:
            result.status = FileStatus.REJECTED
            result.rejection_reason = "File is empty"
            logger.warning("File rejected: empty (%s)", filename)
            return result

        if len(content) > self.max_size:
            result.status = FileStatus.REJECTED
            result.rejection_reason = (
                f"File size {len(content)} exceeds limit {self.max_size}"
            )
            logger.warning("File rejected: too large (%s, %d bytes)", filename, len(content))
            return result

        # 2. Check extension
        _, ext = os.path.splitext(filename.lower())
        result.detected_extension = ext.lstrip(".")

        if ext not in allowed_exts:
            result.status = FileStatus.REJECTED
            result.rejection_reason = f"Extension '{ext}' not in allowlist"
            logger.warning("File rejected: disallowed extension %s (%s)", ext, filename)
            return result

        # 3. Peek at magic bytes / content for additional validation
        #    mimetypes.guess_type() guesses from extension, not content —
        #    we need content inspection to catch disguised files.
        detected_mime, _ = mimetypes.guess_type(filename)
        result.detected_mime = detected_mime or ""

        if len(content) > 0 and ext in ALL_ALLOWED_EXTS:
            text_start = content[:512].decode("utf-8", errors="replace").strip()

            # XML: must start with <?xml or a root element (not HTML/JSON/binary)
            if ext == ".xml":
                is_valid_xml = (
                    text_start.startswith("<?xml")
                    or (text_start.startswith("<")
                        and not text_start.startswith("<!DOCTYPE")
                        and not text_start.startswith("<html")
                        and not text_start.startswith("<HTML")
                        and not text_start.startswith("<head")
                        and not text_start.startswith("<body")
                        and not text_start.startswith("<?php")
                        and not text_start.startswith("<?"))
                )
                if not is_valid_xml:
                    result.status = FileStatus.QUARANTINE
                    result.rejection_reason = "XML extension but content is not XML"
                    logger.warning("File quarantined: not XML content (%s)", filename)
                    if self.quarantine_dir:
                        quarantine_path = self.quarantine_dir / filename
                        quarantine_path.write_bytes(content)
                    return result

            # JSON: must start with { or [
            if ext == ".json" and not text_start.startswith(("{", "[")):
                    result.status = FileStatus.QUARANTINE
                    result.rejection_reason = "JSON extension but content is not JSON"
                    logger.warning("File quarantined: not JSON content (%s)", filename)
                    if self.quarantine_dir:
                        quarantine_path = self.quarantine_dir / filename
                        quarantine_path.write_bytes(content)
                    return result

            # CSV: must contain commas or be valid plain text with rows
            if ext == ".csv" and text_start and text_start.startswith(("<", "<?xml")):
                    result.status = FileStatus.QUARANTINE
                    result.rejection_reason = "CSV extension but content is not CSV"
                    logger.warning("File quarantined: not CSV content (%s)", filename)
                    if self.quarantine_dir:
                        quarantine_path = self.quarantine_dir / filename
                        quarantine_path.write_bytes(content)
                    return result

        # 4. MIME strict check (extension-based guess)
        if detected_mime and self.strict_mime and detected_mime not in allowed_mimes:
                result.status = FileStatus.QUARANTINE
                result.rejection_reason = (
                    f"MIME mismatch: extension={ext}, detected_mime={detected_mime}"
                )
                logger.warning(
                    "File quarantined: MIME mismatch (%s, ext=%s, mime=%s)",
                    filename, ext, detected_mime,
                )
                if self.quarantine_dir:
                    quarantine_path = self.quarantine_dir / filename
                    quarantine_path.write_bytes(content)
                    logger.info("Quarantined file written to %s", quarantine_path)
                return result

        result.status = FileStatus.ALLOWED
        return result

    def validate_upload_file(self, filename: str, content: bytes, **kwargs) -> ValidationResult:
        """Alias para validate con nombre mas descriptivo."""
        return self.validate(filename, content, **kwargs)
