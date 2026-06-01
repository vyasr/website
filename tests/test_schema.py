# pyright: reportArgumentType=false, reportMissingImports=false, reportMissingParameterType=false, reportMissingTypeArgument=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUntypedFunctionDecorator=false, reportUnusedCallResult=false

from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from scripts.lib.schema import (
    Affiliation,
    Education,
    Experience,
    Grant,
    Honor,
    PersonalInfo,
    ProfessionalData,
    Project,
    PublicationRef,
    PresentationRef,
    Service,
    Skill,
    Summary,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return cast(dict, YAML(typ="safe").load(FIXTURES / name))


def test_schema_version_1_0_validates():
    data = ProfessionalData.model_validate(load_fixture("minimal_valid.yaml"))

    assert data.schema_version == "1.0"


def test_schema_version_must_be_1_0():
    payload = load_fixture("minimal_valid.yaml")
    payload["schema_version"] = "2.0"

    with pytest.raises(ValidationError, match="schema_version must be '1.0'"):
        ProfessionalData.model_validate(payload)


def test_minimal_valid_fixture_validates():
    data = ProfessionalData.model_validate(load_fixture("minimal_valid.yaml"))

    assert data.personal_info.name == "Vyas Ramasubramani"
    assert data.education[0].id == "umich-phd"
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


def test_education_dual_variant_fixture_validates_separate_entries():
    data = ProfessionalData.model_validate(load_fixture("education_dual_variant.yaml"))

    assert [entry.id for entry in data.education] == ["umich-phd", "umich-ms"]


def test_invalid_missing_required_fixture_is_rejected():
    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(load_fixture("invalid_missing_required.yaml"))


def test_education_id_field_is_required_and_first():
    assert list(Education.model_fields)[0] == "id"
    with pytest.raises(ValidationError):
        Education.model_validate(
            {
                "institution": "Princeton University",
                "degree": "B.S.E. in Chemical Engineering",
                "area": "Chemical Engineering",
                "start": "2009",
                "end": "2013",
                "location": "Princeton, NJ",
            }
        )


def test_experience_id_field_is_required_and_first():
    assert list(Experience.model_fields)[0] == "id"
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {
                "organization": "NVIDIA",
                "role": "Senior Software Engineer",
                "start": "Mar 2020",
                "end": "Present",
                "location": "Santa Clara, CA",
            }
        )


def test_project_id_field_is_required_and_first():
    assert list(Project.model_fields)[0] == "id"
    with pytest.raises(ValidationError):
        Project.model_validate({"name": "signac framework"})


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Honor, {"title": "Award"}),
        (Service, {"role": "Reviewer", "organization": "Journal"}),
        (Skill, {"category": "Languages", "items": ["Python"]}),
        (Grant, {"title": "Grant", "funder": "NSF", "role": "PI"}),
        (Affiliation, {"organization": "SIAM"}),
    ],
)
def test_other_entry_models_require_id_as_first_field(model, payload):
    assert list(model.model_fields)[0] == "id"
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_formatted_field_accepts_correct_structure():
    project = Project.model_validate(
        {
            "id": "signac-framework",
            "name": "signac framework",
            "formatted": {"name": {"latex": "signac ({\\tiny github.com/glotzerlab/signac})"}},
        }
    )

    assert project.formatted == {
        "name": {"latex": "signac ({\\tiny github.com/glotzerlab/signac})"}
    }


@pytest.mark.parametrize(
    "entry",
    [
        Education(
            id="princeton-bse",
            institution="Princeton University",
            degree="B.S.E.",
            area="Chemical Engineering",
            start="2009",
            end="2013",
            location="Princeton, NJ",
        ),
        Experience(
            id="nvidia-senior-swe",
            organization="NVIDIA",
            role="Senior Software Engineer",
            start="Mar 2020",
            end="Present",
            location="Santa Clara, CA",
        ),
        Project(id="signac-framework", name="signac framework"),
        Skill(id="languages", category="Languages", items=["Python"]),
    ],
)
def test_formatted_field_is_none_by_default(entry):
    assert entry.formatted is None


def test_formatted_field_can_have_multiple_field_entries():
    skill = Skill.model_validate(
        {
            "id": "languages",
            "category": "Languages",
            "items": ["Python", "C++"],
            "formatted": {
                "category": {"html": "Programming languages"},
                "items": {"latex": "\\textsc{expert}: Python, C++"},
            },
        }
    )

    assert skill.formatted == {
        "category": {"html": "Programming languages"},
        "items": {"latex": "\\textsc{expert}: Python, C++"},
    }


def test_publication_ref_has_only_cite_key_and_rejects_display():
    assert set(PublicationRef.model_fields) == {"cite_key"}
    with pytest.raises(ValidationError):
        PublicationRef.model_validate({"cite_key": "paper", "display": {"compact": True}})


def test_presentation_ref_has_only_cite_key_and_rejects_display():
    assert set(PresentationRef.model_fields) == {"cite_key"}
    with pytest.raises(ValidationError):
        PresentationRef.model_validate({"cite_key": "talk", "display": {"compact": True}})


def test_professional_data_has_no_cv_config_field_and_rejects_it():
    assert "cv_config" not in ProfessionalData.model_fields
    payload = load_fixture("minimal_valid.yaml")
    payload["cv_config"] = {"citations_mode": "selectedpubs"}

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)


def test_notes_field_still_works():
    honor = Honor(id="award", title="Award", notes="Internal note")

    assert honor.notes == "Internal note"



def test_summary_still_works():
    summary = Summary(text="Computational scientist.")

    assert summary.text == "Computational scientist."



def test_personal_info_unchanged():
    info = PersonalInfo(
        name="Vyas Ramasubramani",
        email="vyas.ramasubramani@gmail.com",
        phone="(+1) 408-421-2162",
        website="vyasr.com",
        github="vyasr",
        linkedin="vyas-ramasubramani",
        location="Santa Clara, CA",
    )

    assert info.name == "Vyas Ramasubramani"
    assert info.location == "Santa Clara, CA"


@pytest.mark.parametrize("details", ["Minors: QCB", ["Minor: QCB", "Minor: CS"], None])
def test_education_details_accepts_string_list_or_none(details):
    education = Education(
        id="princeton-bse",
        institution="Princeton University",
        degree="B.S.E. in Chemical Engineering",
        area="Chemical Engineering",
        start="2009",
        end="2013",
        location="Princeton, NJ",
        details=details,
    )

    assert education.details == details


def test_experience_bullets_defaults_to_empty_list():
    experience = Experience(
        id="nvidia-senior-swe",
        organization="NVIDIA",
        role="Senior Software Engineer",
        start="Mar 2020",
        end="Present",
        location="Santa Clara, CA",
    )

    assert experience.bullets == []


def test_honor_issuer_is_optional():
    honor = Honor(id="award", title="Award")

    assert honor.issuer is None



def test_grant_amount_is_optional():
    grant = Grant(id="grant", title="Grant", funder="NSF", role="PI")

    assert grant.amount is None



def test_full_professional_data_with_all_sections_validates():
    data = ProfessionalData(
        schema_version="1.0",
        personal_info=PersonalInfo(name="Name", email="name@example.com"),
        education=[
            Education(
                id="edu",
                institution="Institution",
                degree="Degree",
                area="Area",
                start="2020",
                end="2024",
                location="City",
            )
        ],
        research_experience=[
            Experience(
                id="research",
                organization="Org",
                role="Role",
                start="2020",
                end="2021",
                location="City",
            )
        ],
        work_experience=[
            Experience(
                id="work",
                organization="Org",
                role="Role",
                start="2021",
                end="2022",
                location="City",
            )
        ],
        skills=[Skill(id="skill", category="Languages", items=["Python"])],
        projects=[Project(id="project", name="Project")],
        honors=[Honor(id="honor", title="Honor")],
        service_leadership=[Service(id="service", role="Role", organization="Org")],
        teaching_experience=[
            Experience(
                id="teaching",
                organization="Org",
                role="Role",
                start="2022",
                end="2023",
                location="City",
            )
        ],
        grants=[Grant(id="grant", title="Grant", funder="Funder", role="PI")],
        extracurricular=[
            Experience(
                id="extra",
                organization="Org",
                role="Role",
                start="2023",
                end="2024",
                location="City",
            )
        ],
        affiliations=[Affiliation(id="affiliation", organization="Org")],
        wetlab_skills=[Skill(id="wetlab", category="Wet lab", items=["PCR"])],
        summary=Summary(text="Summary"),
        publications=[PublicationRef(cite_key="paper")],
        presentations=[PresentationRef(cite_key="talk")],
    )

    assert data.publications[0].cite_key == "paper"


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


def test_skill_items_must_be_a_list():
    with pytest.raises(ValidationError):
        Skill.model_validate({"id": "languages", "category": "Languages", "items": "Python, C++"})


def test_missing_required_publication_cite_key_raises_validation_error():
    payload = load_fixture("minimal_valid.yaml")
    del payload["publications"][0]["cite_key"]

    with pytest.raises(ValidationError):
        ProfessionalData.model_validate(payload)
