# pyright: reportArgumentType=false, reportMissingImports=false, reportMissingParameterType=false, reportMissingTypeArgument=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUntypedFunctionDecorator=false, reportUnusedCallResult=false

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from scripts.lib.schema import (
    CVConfig,
    DisplayConfig,
    Education,
    Experience,
    Grant,
    ProfessionalData,
    PublicationRef,
    PresentationRef,
    Skill,
    Summary,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return YAML(typ="safe").load(FIXTURES / name)


def test_minimal_valid_fixture_validates():
    data = ProfessionalData.model_validate(load_fixture("minimal_valid.yaml"))

    assert data.schema_version == "1.0"
    assert data.personal_info.name == "Vyas Ramasubramani"
    assert len(data.education) == 1
    assert len(data.publications) == 1


def test_full_valid_fixture_validates_with_all_sections_populated():
    data = ProfessionalData.model_validate(load_fixture("full_valid.yaml"))

    assert data.summary is not None
    assert data.research_experience
    assert data.work_experience
    assert data.skills
    assert data.projects
    assert data.honors
    assert data.service_leadership
    assert data.teaching_experience
    assert data.grants
    assert data.extracurricular
    assert data.affiliations
    assert data.wetlab_skills
    assert data.presentations


def test_schema_version_must_be_1_0():
    payload = load_fixture("minimal_valid.yaml")
    payload["schema_version"] = "2.0"

    with pytest.raises(ValidationError, match="schema_version must be '1.0'"):
        ProfessionalData.model_validate(payload)


def test_display_config_defaults_show_in_compact_and_extended_not_outdated():
    display = DisplayConfig()

    assert display.compact is True
    assert display.extended is True
    assert display.outdated is False


def test_education_with_compact_override_validates():
    data = ProfessionalData.model_validate(load_fixture("education_dual_variant.yaml"))

    education = data.education[0]

    assert education.compact_override is not None
    assert education.compact_override.degree == "Ph.D. in Chemical Engineering"


def test_education_compact_override_must_be_valid_education():
    payload = load_fixture("education_dual_variant.yaml")
    del payload["education"][0]["compact_override"]["institution"]

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)


def test_publication_ref_has_only_cite_key_and_display_fields():
    fields = set(PublicationRef.model_fields)

    assert fields == {"cite_key", "display"}


def test_publication_ref_rejects_author_title_venue_fields():
    with pytest.raises(ValidationError):
        PublicationRef.model_validate(
            {"cite_key": "paper", "author": "Author", "title": "Title", "venue": "Venue"}
        )


def test_presentation_ref_has_only_cite_key_and_display_fields():
    fields = set(PresentationRef.model_fields)

    assert fields == {"cite_key", "display"}


def test_presentation_ref_rejects_author_title_venue_fields():
    with pytest.raises(ValidationError):
        PresentationRef.model_validate({"cite_key": "talk", "author": "Author"})


@pytest.mark.parametrize(
    "mode", ["selectedpubs", "all", "none", "combinepubs"]
)
def test_cv_config_citations_mode_accepts_valid_values(mode):
    config = CVConfig(citations_mode=mode)

    assert config.citations_mode == mode


def test_cv_config_citations_mode_rejects_invalid_value():
    with pytest.raises(ValidationError):
        CVConfig(citations_mode="selected")


def test_missing_required_personal_info_name_raises_validation_error():
    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(load_fixture("invalid_missing_required.yaml"))


def test_missing_required_education_institution_raises_validation_error():
    payload = load_fixture("minimal_valid.yaml")
    del payload["education"][0]["institution"]

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)


def test_missing_required_publication_cite_key_raises_validation_error():
    payload = load_fixture("minimal_valid.yaml")
    del payload["publications"][0]["cite_key"]

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)


def test_experience_bullets_defaults_to_empty_list():
    experience = Experience(
        organization="NVIDIA",
        role="Senior Software Engineer",
        start="Mar 2020",
        end="Present",
        location="Santa Clara, CA",
    )

    assert experience.bullets == []


def test_display_config_outdated_defaults_to_false():
    assert DisplayConfig().outdated is False


def test_skill_items_must_be_a_list():
    with pytest.raises(ValidationError):
        Skill.model_validate({"category": "Languages", "items": "Python, C++"})


def test_grant_with_amount_none_validates():
    grant = Grant(title="Grant", funder="NSF", role="PI", amount=None)

    assert grant.amount is None


def test_summary_text_is_required():
    with pytest.raises(ValidationError):
        Summary.model_validate({})


def test_professional_data_accepts_empty_section_lists():
    payload = load_fixture("minimal_valid.yaml")
    for section in (
        "education",
        "research_experience",
        "work_experience",
        "skills",
        "projects",
        "honors",
        "service_leadership",
        "teaching_experience",
        "grants",
        "extracurricular",
        "affiliations",
        "wetlab_skills",
        "publications",
        "presentations",
    ):
        payload[section] = []

    data = ProfessionalData.model_validate(payload)

    assert data.education == []
    assert data.publications == []


@pytest.mark.parametrize("details", ["Minors: QCB", ["Minor: QCB", "Minor: CS"], None])
def test_education_details_accepts_string_list_or_none(details):
    education = Education(
        institution="Princeton University",
        degree="B.S.E. in Chemical Engineering",
        area="Chemical Engineering",
        start="2009",
        end="2013",
        location="Princeton, NJ",
        details=details,
    )

    assert education.details == details


def test_selected_publications_order_is_preserved():
    data = ProfessionalData.model_validate(load_fixture("full_valid.yaml"))

    assert data.cv_config.selected_publications == [
        "Ramasubramani2020b",
        "Ramasubramani2020",
        "Dice_2019",
    ]


def test_project_latex_overrides_validate_as_string_mapping():
    data = ProfessionalData.model_validate(load_fixture("full_valid.yaml"))

    assert data.projects[0].latex_overrides == {
        "name": "signac framework ({\\tiny github.com/glotzerlab/signac})"
    }


def test_display_tags_validate_on_full_fixture_entries():
    data = ProfessionalData.model_validate(load_fixture("full_valid.yaml"))

    assert data.honors[0].display.extended is False
    assert data.honors[1].display.outdated is True


def test_invalid_skill_items_in_fixture_is_rejected():
    payload = load_fixture("minimal_valid.yaml")
    payload["skills"] = [{"category": "Languages", "items": "Python"}]

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)
