"""Tests for file validation service."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.file_validation import (
    FileStatus,
    FileValidator,
)


class TestFileValidation:
    def setup_method(self):
        self.validator = FileValidator(max_size=1024 * 1024)  # 1MB for tests

    def test_empty_file_rejected(self):
        result = self.validator.validate("test.xml", b"")
        assert result.status == FileStatus.REJECTED
        assert result.rejection_reason == "File is empty"

    def test_large_file_rejected(self):
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        result = self.validator.validate("test.xml", content)
        assert result.status == FileStatus.REJECTED
        assert "exceeds limit" in result.rejection_reason

    def test_allowed_xml_file(self):
        content = b'<?xml version="1.0"?><root><item>test</item></root>'
        result = self.validator.validate("test.xml", content, allowed_types=["xml"])
        assert result.status == FileStatus.ALLOWED

    def test_allowed_csv_file(self):
        content = b"a,b,c\n1,2,3"
        result = self.validator.validate("data.csv", content, allowed_types=["csv"])
        assert result.status == FileStatus.ALLOWED

    def test_allowed_json_file(self):
        content = b'{"key": "value"}'
        result = self.validator.validate("data.json", content, allowed_types=["json"])
        assert result.status == FileStatus.ALLOWED

    def test_disallowed_extension_rejected(self):
        content = b"some content"
        result = self.validator.validate("malware.exe", content, allowed_types=["xml"])
        assert result.status == FileStatus.REJECTED
        assert "not in allowlist" in result.rejection_reason

    def test_mime_mismatch_quarantined(self):
        """File says .xml but content is not XML -> quarantine (content check catches it first)."""
        content = b'{"key": "value"}'  # JSON content
        result = self.validator.validate("fake.xml", content, allowed_types=["xml"])
        assert result.status == FileStatus.QUARANTINE
        assert "content is not XML" in result.rejection_reason

    def test_xml_content_validation(self):
        """XML extension but content starts with HTML -> quarantine."""
        content = b"<!DOCTYPE html><html></html>"  # HTML content
        result = self.validator.validate("document.xml", content, allowed_types=["xml"])
        assert result.status == FileStatus.QUARANTINE
        assert "content is not XML" in result.rejection_reason

    def test_pdf_allowed(self):
        # Fake PDF magic bytes
        content = b"%PDF-1.4 fake pdf content"
        result = self.validator.validate("doc.pdf", content, allowed_types=["pdf"])
        assert result.status == FileStatus.ALLOWED

    def test_quarantine_dir_created(self, tmp_path):
        quarantine = tmp_path / "quarantine"
        validator = FileValidator(max_size=1024 * 1024, quarantine_dir=str(quarantine))
        content = b'{"key": "value"}'
        result = validator.validate("fake.xml", content, allowed_types=["xml"])
        assert result.status == FileStatus.QUARANTINE
        assert (quarantine / "fake.xml").exists()
        assert (quarantine / "fake.xml").read_bytes() == content

    def test_default_max_size(self):
        validator = FileValidator()
        assert validator.max_size == 50 * 1024 * 1024  # 50MB

    def test_multiple_allowed_types(self):
        content = b"a,b,c\n1,2,3"
        result = self.validator.validate(
            "data.csv",
            content,
            allowed_types=["xml", "csv", "json"],
        )
        assert result.status == FileStatus.ALLOWED

    def test_rejected_when_type_not_in_list(self):
        content = b"<xml>test</xml>"
        result = self.validator.validate("data.xml", content, allowed_types=["csv", "json"])
        assert result.status == FileStatus.REJECTED
        assert "not in allowlist" in result.rejection_reason
