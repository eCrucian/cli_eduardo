from __future__ import annotations

from pathlib import Path

from cli_eduardo.infrastructure.sandbox import read_sandbox_files


def test_reads_text_file(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("hello world", encoding="utf-8")
    result = read_sandbox_files(tmp_path)
    assert "report.txt" in result
    assert "hello world" in result


def test_empty_directory_returns_empty_string(tmp_path: Path) -> None:
    assert read_sandbox_files(tmp_path) == ""


def test_skips_sharepoint_temp_files(tmp_path: Path) -> None:
    (tmp_path / "~$locked.xlsx").write_text("lock", encoding="utf-8")
    (tmp_path / "report.txt").write_text("content", encoding="utf-8")
    result = read_sandbox_files(tmp_path)
    assert "~$locked.xlsx" not in result
    assert "report.txt" in result


def test_multiple_files_appear_in_sorted_order(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    result = read_sandbox_files(tmp_path)
    assert result.index("a.txt") < result.index("b.txt")


def test_skips_subdirectories(tmp_path: Path) -> None:
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "report.txt").write_text("ok", encoding="utf-8")
    result = read_sandbox_files(tmp_path)
    assert "subdir" not in result
    assert "report.txt" in result


def test_formats_as_xml_file_tags(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("text", encoding="utf-8")
    result = read_sandbox_files(tmp_path)
    assert "<file name='report.txt'>" in result
    assert "</file>" in result
