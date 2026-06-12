from __future__ import annotations

from pathlib import Path


def read_sandbox_files(cwd: Path) -> str:
    """Read non-temp files from the sandbox and format them as XML-tagged blocks for LLM context."""
    parts: list[str] = []
    for path in sorted(cwd.iterdir()):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        parts.append(f"<file name={path.name!r}>\n{text}\n</file>")
    return "\n".join(parts)
