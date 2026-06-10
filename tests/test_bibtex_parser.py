from pathlib import Path

from scripts.lib.bibtex_parser import extract_cite_keys, validate_bib_keys_exist


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "external" / "cv-data"


def test_extract_cite_keys_publications():
    keys = extract_cite_keys(DATA_DIR / "Publications.bib")

    assert len(keys) == 11
    assert keys[0] == "Butler2020"
    assert keys[-1] == "adorf2018"


def test_extract_cite_keys_presentations():
    keys = extract_cite_keys(DATA_DIR / "Presentations.bib")

    assert len(keys) == 25
    assert keys[0] == "pycon2026"
    assert keys[-1] == "gibbs2012"


def test_validate_bib_keys_exist_all_present():
    keys = ["Ramasubramani2020b", "Ramasubramani2020", "Dice_2019"]

    missing = validate_bib_keys_exist(keys, DATA_DIR / "Publications.bib")

    assert missing == []


def test_validate_bib_keys_exist_missing():
    keys = ["Ramasubramani2020b", "missing-key", "Dice_2019", "another-missing"]

    missing = validate_bib_keys_exist(keys, DATA_DIR / "Publications.bib")

    assert missing == ["missing-key", "another-missing"]
