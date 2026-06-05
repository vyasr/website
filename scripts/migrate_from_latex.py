from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import BaseModel
from ruamel.yaml import YAML

from scripts.lib.bibtex_parser import extract_cite_keys
from scripts.lib.cv_config import CVConfigRoot, CitationsConfig, EntryConfig, SectionConfig, SectionsConfig
from scripts.lib.latex_parser import (
    determine_display_context,
    expand_local_macros,
    extract_comment_metadata,
    extract_cvhonor,
    extract_cvparagraph,
    extract_cvskill,
    extract_cventry,
    extract_local_macro_defs,
    extract_personal_info,
    extract_selected_publications,
    normalize_text,
)
from scripts.lib.schema import (
    Affiliation,
    Education,
    Experience,
    Grant,
    Honor,
    PersonalInfo,
    PresentationRef,
    ProfessionalData,
    Project,
    PublicationRef,
    Service,
    Skill,
    Summary,
)


ROOT = Path(__file__).resolve().parents[1]
MYCV = ROOT / "external" / "awesome-cv" / "mycv"
CV_DIR = MYCV / "cv"

DisplayMode = Literal["compact", "extended"]
DisplayInfo = dict[str, bool]
Formatted = dict[str, dict[str, str]]


class EntryWithID(Protocol):
    id: str


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def read_source(path: Path) -> str:
    try:
        return path.read_text()
    except OSError as err:
        warn(f"could not read {path}: {err}")
        return ""


def display_from_entry(entry: dict[str, str], content: str) -> DisplayInfo:
    display = determine_display_context(entry.get("_raw", "").splitlines(), content.splitlines())
    return {"compact": display["compact"], "extended": display["extended"]}


def clean(raw: str) -> tuple[str, str | None]:
    text, override = normalize_text(raw)
    return text, override


def clean_field(raw: str, field_name: str, formatted: Formatted) -> str:
    text, override = clean(raw)
    if override is not None:
        formatted[field_name] = {"latex": override}
    return text


def none_if_empty(value: str) -> str | None:
    return value if value else None


def split_dates(raw: str) -> tuple[str, str]:
    text, _ = clean(raw)
    parts = re.split(r"\s+(?:-|–)\s+", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def extract_bullets(cvitems_text: str) -> list[str]:
    match = re.search(r"\\begin\{cvitems\}(.*?)\\end\{cvitems\}", cvitems_text, flags=re.S)
    body = match.group(1) if match else cvitems_text
    bullets: list[str] = []
    for chunk in re.split(r"\\item\b", body)[1:]:
        text, _ = clean(chunk)
        if text:
            bullets.append(text)
    return bullets


def extract_entry_notes(raw: str) -> str | None:
    notes: list[str] = []
    for line in raw.splitlines():
        note = extract_comment_metadata(line)
        if note and not re.fullmatch(
            r"(?:Degree|Institution|Location|Date\(s\)|Job title|Organization|Role|Event|Award|Type|Skillset|Description\(s\).*|Affiliation/role|Organization/group|Position|Affiliation)",
            note,
        ):
            notes.append(note)
    return "; ".join(notes) if notes else None


def area_from_degree(degree: str) -> str:
    if " in " in degree:
        return degree.split(" in ", 1)[1].split(" and ", 1)[0].strip()
    return ""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return re.sub(r"-+", "-", slug).strip("-")


def degree_slug(degree: str) -> str:
    degree_lower = degree.lower()
    if "ph.d" in degree_lower or "phd" in degree_lower:
        return "phd"
    if "m.s" in degree_lower or "ms" in degree_lower:
        return "ms"
    if "b.s" in degree_lower or "bse" in degree_lower or "b.s.e" in degree_lower:
        return "bse"
    return slugify(degree) or "degree"


def org_slug(organization: str) -> str:
    replacements = {
        "University of Michigan": "umich",
        "Princeton University": "princeton",
        "Academy of Sciences of the Czech Republic": "ascr",
        "Stanford University": "stanford",
        "UC Santa Cruz": "ucsc",
    }
    for prefix, replacement in replacements.items():
        if organization.startswith(prefix):
            suffix = organization.removeprefix(prefix).strip(" -")
            return "-".join(part for part in [replacement, slugify(suffix)] if part)
    return slugify(organization) or "entry"


def role_slug(role: str) -> str:
    value = role.lower().replace("software engineer", "swe")
    return slugify(value) or "role"


def unique_id(base: str, used_ids: set[str]) -> str:
    candidate = base or "entry"
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def make_formatted(formatted: Formatted) -> Formatted | None:
    return formatted or None


def display_modes(display: DisplayInfo) -> list[DisplayMode]:
    modes: list[DisplayMode] = []
    if display["compact"]:
        modes.append("compact")
    if display["extended"]:
        modes.append("extended")
    return modes or ["compact", "extended"]


def make_education(
    entry: dict[str, str],
    *,
    used_ids: set[str],
    degree: str | None = None,
    date: str | None = None,
) -> tuple[Education, DisplayInfo]:
    degree_text = degree if degree is not None else clean(entry["arg1"])[0]
    institution = clean(entry["arg2"])[0]
    location = clean(entry["arg3"])[0]
    start, end = split_dates(date if date is not None else entry["arg4"])
    details = clean(entry["arg5"])[0]
    entry_id = unique_id(f"{org_slug(institution)}-{degree_slug(degree_text)}", used_ids)
    return (
        Education(
            id=entry_id,
            institution=institution,
            degree=degree_text,
            area=area_from_degree(degree_text),
            start=start,
            end=end,
            location=location,
            advisor=None,
            details=none_if_empty(details),
            notes=extract_entry_notes(entry.get("_raw", "")),
        ),
        display_from_entry(entry, read_source(CV_DIR / "education.tex")),
    )


def migrate_education(used_ids: set[str]) -> tuple[list[Education], list[DisplayInfo]]:
    content = read_source(CV_DIR / "education.tex")
    entries = extract_cventry(content)
    if len(entries) < 2:
        pairs = [make_education(entry, used_ids=used_ids) for entry in entries]
        return [entry for entry, _ in pairs], [display for _, display in pairs]

    full_entry = entries[1]
    degree_parts = [part.strip() for part in full_entry["arg1"].split("\\linebreak") if part.strip()]
    date_parts = [part.strip() for part in full_entry["arg4"].split("\\linebreak") if part.strip()]

    migrated: list[Education] = []
    displays: list[DisplayInfo] = []
    for index, degree in enumerate(degree_parts or [full_entry["arg1"]]):
        education, display = make_education(
            full_entry,
            used_ids=used_ids,
            degree=clean(degree)[0],
            date=date_parts[index] if index < len(date_parts) else full_entry["arg4"],
        )
        if education.id == "umich-ms":
            display = {"compact": False, "extended": True}
        migrated.append(education)
        displays.append(display)
    for entry in entries[2:]:
        education, display = make_education(entry, used_ids=used_ids)
        migrated.append(education)
        displays.append(display)
    return migrated, displays


def make_experience(entry: dict[str, str], content: str, *, used_ids: set[str]) -> tuple[Experience, DisplayInfo]:
    formatted: Formatted = {}
    role = clean_field(entry["arg1"], "role", formatted)
    organization = clean_field(entry["arg2"], "organization", formatted)
    location = clean_field(entry["arg3"], "location", formatted)
    start, end = split_dates(entry["arg4"])
    body_text, body_override = clean(entry["arg5"])
    if body_override is not None:
        formatted["summary"] = {"latex": body_override}
    bullets = extract_bullets(entry["arg5"])
    summary = none_if_empty(body_text) if not bullets else None
    return (
        Experience(
            id=unique_id(f"{org_slug(organization)}-{role_slug(role)}", used_ids),
            organization=organization,
            role=role,
            start=start,
            end=end,
            location=location,
            summary=summary,
            bullets=bullets,
            formatted=make_formatted(formatted),
            notes=extract_entry_notes(entry.get("_raw", "")),
        ),
        display_from_entry(entry, content),
    )


def migrate_experience(filename: str, used_ids: set[str], *, expand_macros: bool = False) -> tuple[list[Experience], list[DisplayInfo]]:
    content = read_source(CV_DIR / filename)
    if expand_macros:
        content = expand_local_macros(content, extract_local_macro_defs(content))
    pairs = [make_experience(entry, content, used_ids=used_ids) for entry in extract_cventry(content)]
    return [entry for entry, _ in pairs], [display for _, display in pairs]


def split_skill_items(text: str) -> list[str]:
    items = [item.strip() for item in text.split(",") if item.strip()]
    return items or ([text] if text else [])


def migrate_skills(filename: str, used_ids: set[str]) -> tuple[list[Skill], list[DisplayInfo]]:
    content = read_source(CV_DIR / filename)
    skills: list[Skill] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cvskill(content):
        formatted: Formatted = {}
        category = clean_field(entry["arg1"], "category", formatted)
        description = clean_field(entry["arg2"], "items", formatted)
        skills.append(
            Skill(
                id=unique_id(slugify(category), used_ids),
                category=category,
                items=split_skill_items(description),
                formatted=make_formatted(formatted),
            )
        )
        displays.append(display_from_entry(entry, content))
    return skills, displays


def migrate_projects(used_ids: set[str]) -> tuple[list[Project], list[DisplayInfo]]:
    content = read_source(CV_DIR / "projects.tex")
    projects: list[Project] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cventry(content):
        formatted: Formatted = {}
        role = clean_field(entry["arg1"], "summary", formatted)
        name = clean_field(entry["arg2"], "name", formatted)
        projects.append(
            Project(
                id=unique_id(slugify(name), used_ids),
                name=name,
                url=None,
                summary=none_if_empty(role),
                bullets=extract_bullets(entry["arg5"]),
                technologies=[],
                formatted=make_formatted(formatted),
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
        displays.append(display_from_entry(entry, content))
    return projects, displays


def migrate_honors(filename: str, used_ids: set[str]) -> tuple[list[Honor], list[DisplayInfo]]:
    content = read_source(CV_DIR / filename)
    honors: list[Honor] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cvhonor(content):
        title = clean(entry["arg1"])[0]
        issuer = none_if_empty(clean(entry["arg2"])[0])
        honors.append(
            Honor(
                id=unique_id(slugify("-".join(part for part in [title, issuer or ""] if part)), used_ids),
                title=title,
                issuer=issuer,
                location=none_if_empty(clean(entry["arg3"])[0]),
                date=none_if_empty(clean(entry["arg4"])[0]),
                summary=None,
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
        displays.append(display_from_entry(entry, content))
    return honors, displays


def migrate_service(used_ids: set[str]) -> tuple[list[Service], list[DisplayInfo]]:
    content = read_source(CV_DIR / "serviceleadership.tex")
    services: list[Service] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cvhonor(content):
        role = clean(entry["arg1"])[0]
        organization = clean(entry["arg2"])[0]
        services.append(
            Service(
                id=unique_id(slugify(f"{organization}-{role}"), used_ids),
                role=role,
                organization=organization,
                location=none_if_empty(clean(entry["arg3"])[0]),
                date=none_if_empty(clean(entry["arg4"])[0]),
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
        displays.append(display_from_entry(entry, content))
    return services, displays


def migrate_grants(used_ids: set[str]) -> tuple[list[Grant], list[DisplayInfo]]:
    content = read_source(CV_DIR / "grants.tex")
    grants: list[Grant] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cventry(content):
        start, end = split_dates(entry["arg4"])
        title = clean(entry["arg2"])[0]
        grants.append(
            Grant(
                id=unique_id(slugify("-".join([title, start])), used_ids),
                title=title,
                funder=clean(entry["arg3"])[0],
                role="Contributor",
                amount=none_if_empty(clean(entry["arg1"])[0]),
                start=none_if_empty(start),
                end=none_if_empty(end),
                details=extract_bullets(entry["arg5"]),
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
        displays.append(display_from_entry(entry, content))
    return grants, displays


def migrate_affiliations(used_ids: set[str]) -> tuple[list[Affiliation], list[DisplayInfo]]:
    content = read_source(CV_DIR / "affiliations.tex")
    affiliations: list[Affiliation] = []
    displays: list[DisplayInfo] = []
    for entry in extract_cvhonor(content):
        organization = clean(entry["arg2"])[0]
        affiliations.append(
            Affiliation(
                id=unique_id(slugify(organization), used_ids),
                organization=organization,
                role=none_if_empty(clean(entry["arg1"])[0]),
                date=none_if_empty(clean(entry["arg4"])[0]),
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
        displays.append(display_from_entry(entry, content))
    return affiliations, displays


def migrate_summary() -> Summary | None:
    content = read_source(CV_DIR / "summary.tex")
    paragraph = extract_cvparagraph(content)
    if paragraph is None:
        return None
    text, _ = clean(paragraph)
    text = re.sub(r"^(?:%-+\s*)+", "", text).strip()
    return Summary(text=text)


def make_personal_info(cv_tex: str) -> PersonalInfo:
    info = extract_personal_info(cv_tex)
    return PersonalInfo(
        name=info.get("name", ""),
        email=info.get("email", ""),
        phone=info.get("mobile"),
        website=info.get("homepage"),
        github=info.get("github"),
        linkedin=info.get("linkedin"),
        location=None,
    )


def section_config(entries: Sequence[EntryWithID], displays: Sequence[DisplayInfo]) -> SectionConfig:
    return SectionConfig(
        entries=[
            EntryConfig(id=str(entry.id), display=display_modes(display))
            for entry, display in zip(entries, displays, strict=True)
        ]
    )


def build_data_and_config() -> tuple[ProfessionalData, CVConfigRoot]:
    cv_tex = read_source(MYCV / "cv.tex")
    used_ids: set[str] = set()
    education, education_display = migrate_education(used_ids)
    research, research_display = migrate_experience("researchexperience.tex", used_ids, expand_macros=True)
    work, work_display = migrate_experience("workexperience.tex", used_ids)
    skills, skills_display = migrate_skills("skills.tex", used_ids)
    projects, projects_display = migrate_projects(used_ids)
    honors, honors_display = migrate_honors("honors.tex", used_ids)
    service, service_display = migrate_service(used_ids)
    teaching, teaching_display = migrate_experience("teachingexperience.tex", used_ids)
    grants, grants_display = migrate_grants(used_ids)
    extracurricular, extracurricular_display = migrate_experience("extracurricular.tex", used_ids)
    affiliations, affiliations_display = migrate_affiliations(used_ids)
    wetlab_skills, wetlab_skills_display = migrate_skills("wetlabskills.tex", used_ids)

    data = ProfessionalData(
        schema_version="1.0",
        personal_info=make_personal_info(cv_tex),
        education=education,
        research_experience=research,
        work_experience=work,
        skills=skills,
        projects=projects,
        honors=honors,
        service_leadership=service,
        teaching_experience=teaching,
        grants=grants,
        extracurricular=extracurricular,
        affiliations=affiliations,
        wetlab_skills=wetlab_skills,
        summary=migrate_summary(),
        publications=[PublicationRef(cite_key=key) for key in extract_cite_keys(MYCV / "Publications.bib")],
        presentations=[PresentationRef(cite_key=key) for key in extract_cite_keys(MYCV / "Presentations.bib")],
    )
    config = CVConfigRoot(
        schema_version="1.0",
        citations=CitationsConfig(mode="selectedpubs", selected=extract_selected_publications(cv_tex)),
        sections=SectionsConfig(
            education=section_config(education, education_display),
            research_experience=section_config(research, research_display),
            work_experience=section_config(work, work_display),
            skills=section_config(skills, skills_display),
            projects=section_config(projects, projects_display),
            honors=section_config(honors, honors_display),
            service_leadership=section_config(service, service_display),
            teaching_experience=section_config(teaching, teaching_display),
            grants=section_config(grants, grants_display),
            extracurricular=section_config(extracurricular, extracurricular_display),
            affiliations=section_config(affiliations, affiliations_display),
            wetlab_skills=section_config(wetlab_skills, wetlab_skills_display),
        ),
    )
    return ProfessionalData.model_validate(data.model_dump()), CVConfigRoot.model_validate(config.model_dump())


def write_yaml(data: BaseModel, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)  # pyright: ignore[reportAny]
    with output_path.open("w") as handle:
        yaml.dump(data.model_dump(by_alias=False), handle)  # pyright: ignore[reportUnknownMemberType]


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AwesomeCV LaTeX data to validated YAML.")
    _ = parser.add_argument("--data-output", default=str(ROOT / "data" / "professional.yaml"), help="Professional data YAML path")
    _ = parser.add_argument("--cv-config-output", default=str(ROOT / "cv" / "config.yaml"), help="CV config YAML path")
    args: argparse.Namespace = parser.parse_args()

    data, config = build_data_and_config()
    data_output = Path(str(cast(str, args.data_output)))
    config_output = Path(str(cast(str, args.cv_config_output)))
    write_yaml(data, data_output)
    write_yaml(config, config_output)
    print(f"Wrote {data_output}")
    print(f"Wrote {config_output}")
    counts = (
        f"Counts: education={len(data.education)}, research={len(data.research_experience)}, "
        f"work={len(data.work_experience)}, projects={len(data.projects)}, honors={len(data.honors)}, "
        f"publications={len(data.publications)}, presentations={len(data.presentations)}"
    )
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
