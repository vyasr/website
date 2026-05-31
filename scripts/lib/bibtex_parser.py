from __future__ import annotations

from pathlib import Path
import re


def extract_cite_keys(bib_path: str | Path) -> list[str]:
    content = Path(bib_path).read_text()
    return [match.group(1).strip() for match in re.finditer(r"@\w+\s*\{\s*([^,]+)\s*,", content)]


def validate_bib_keys_exist(keys: list[str], bib_path: str | Path) -> list[str]:
    existing = set(extract_cite_keys(bib_path))
    return [key for key in keys if key not in existing]
