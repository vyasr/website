from pathlib import Path

from scripts.lib.bibtex_parser import extract_cite_keys, validate_bib_keys_exist


ROOT = Path(__file__).resolve().parents[1]
MYCV_DIR = ROOT / "external" / "awesome-cv" / "mycv"


def test_extract_cite_keys_publications():
    keys = extract_cite_keys(MYCV_DIR / "Publications.bib")

    assert len(keys) == 11
    assert keys[0] == "Butler2020"
    assert keys[-1] == "adorf2018"


def test_extract_cite_keys_presentations():
    keys = extract_cite_keys(MYCV_DIR / "Presentations.bib")

    assert len(keys) == 21
    assert keys[0] == "ramasubramaniaiche2019a"
    assert keys[-1] == "gibbs2012"


def test_validate_bib_keys_exist_all_present():
    keys = ["Ramasubramani2020b", "Ramasubramani2020", "Dice_2019"]

    missing = validate_bib_keys_exist(keys, MYCV_DIR / "Publications.bib")

    assert missing == []


def test_validate_bib_keys_exist_missing():
    keys = ["Ramasubramani2020b", "missing-key", "Dice_2019", "another-missing"]

    missing = validate_bib_keys_exist(keys, MYCV_DIR / "Publications.bib")

    assert missing == ["missing-key", "another-missing"]
