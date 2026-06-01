# pyright: reportExplicitAny=false, reportUnknownMemberType=false

from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from scripts.lib.cv_config import (
    CVConfigRoot,
    CitationsConfig,
    EntryConfig,
    SectionConfig,
    SectionsConfig,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], YAML(typ="safe").load(FIXTURES / name))


def minimal_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "citations": {"mode": "none", "selected": []},
        "sections": {},
    }


def test_minimal_config_validates():
    config = CVConfigRoot.model_validate(minimal_payload())

    assert config.citations.mode == "none"
    assert config.sections.education is None


def test_full_config_validates():
    config = CVConfigRoot.model_validate(load_fixture("cv_config_valid.yaml"))

    assert config.citations.mode == "selectedpubs"
    assert config.sections.education is not None
    assert config.sections.research_experience is not None
    assert config.sections.work_experience is not None
    assert config.sections.skills is not None
    assert config.sections.projects is not None
    assert config.sections.honors is not None
    assert config.sections.service_leadership is not None
    assert config.sections.teaching_experience is not None
    assert config.sections.grants is not None
    assert config.sections.extracurricular is not None
    assert config.sections.affiliations is not None
    assert config.sections.wetlab_skills is not None


def test_schema_version_1_0_accepts():
    config = CVConfigRoot.model_validate(minimal_payload())

    assert config.schema_version == "1.0"


def test_schema_version_wrong_rejects():
    payload = minimal_payload()
    payload["schema_version"] = "2.0"

    with pytest.raises(ValidationError, match="schema_version must be '1.0'"):
        _ = CVConfigRoot.model_validate(payload)


def test_entry_config_defaults():
    entry = EntryConfig(id="umich-phd")

    assert entry.display == ["compact", "extended"]
    assert entry.outdated is False


def test_entry_config_compact_only():
    entry = EntryConfig.model_validate({"id": "umich-phd", "display": ["compact"]})

    assert entry.display == ["compact"]


def test_entry_config_extended_only():
    entry = EntryConfig.model_validate({"id": "umich-ms", "display": ["extended"]})

    assert entry.display == ["extended"]


def test_entry_config_outdated_true():
    entry = EntryConfig.model_validate({"id": "lynbrook-hs", "outdated": True})

    assert entry.outdated is True


def test_entry_config_missing_id_rejects():
    with pytest.raises(ValidationError):
        _ = EntryConfig.model_validate({"display": ["compact"]})


@pytest.mark.parametrize("mode", ["selectedpubs", "all", "none", "combinepubs"])
def test_citations_mode_valid_values(mode: str):
    citations = CitationsConfig.model_validate({"mode": mode})

    assert citations.mode == mode


def test_citations_mode_invalid_rejects():
    with pytest.raises(ValidationError):
        _ = CitationsConfig.model_validate({"mode": "selected"})


def test_citations_selected_order_preserved():
    selected = ["Ramasubramani2020b", "Ramasubramani2020", "Dice_2019"]
    citations = CitationsConfig.model_validate(
        {"mode": "selectedpubs", "selected": selected}
    )

    assert citations.selected == selected


def test_section_config_empty_entries_valid():
    section = SectionConfig.model_validate({"entries": []})

    assert section.entries == []


def test_sections_config_all_none_valid():
    sections = SectionsConfig()

    assert sections.education is None
    assert sections.wetlab_skills is None


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        _ = EntryConfig.model_validate({"id": "umich-phd", "unknown": True})


def test_unknown_section_name_rejected():
    with pytest.raises(ValidationError):
        _ = SectionsConfig.model_validate({"unknown_section": {"entries": []}})


def test_invalid_display_value_rejects():
    with pytest.raises(ValidationError):
        _ = EntryConfig.model_validate({"id": "umich-phd", "display": ["full"]})


def test_fixture_valid_loads():
    config = CVConfigRoot.model_validate(load_fixture("cv_config_valid.yaml"))

    assert config.sections.education is not None
    assert config.sections.education.entries[0].id == "umich-phd"


def test_fixture_minimal_loads():
    config = CVConfigRoot.model_validate(load_fixture("cv_config_minimal.yaml"))

    assert config.citations.mode == "none"
    assert config.sections.education is not None
    assert config.sections.education.entries[0].display == ["compact", "extended"]
