from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML  # pyright: ignore[reportMissingImports, reportUnknownVariableType]

from scripts.lib.bibtex_parser import extract_cite_keys
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
    CVConfig,
    DisplayConfig,
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


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def read_source(path: Path) -> str:
    try:
        return path.read_text()
    except OSError as err:
        warn(f"could not read {path}: {err}")
        return ""


def display_from_entry(entry: dict[str, str], content: str) -> DisplayConfig:
    return DisplayConfig(**determine_display_context(entry.get("_raw", "").splitlines(), content.splitlines()))


def clean(raw: str) -> tuple[str, str | None]:
    text, override = normalize_text(raw)
    return text, override


def clean_field(raw: str, field_name: str, overrides: dict[str, str]) -> str:
    text, override = clean(raw)
    if override is not None:
        overrides[field_name] = override
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
        if note and not re.fullmatch(r"(?:Degree|Institution|Location|Date\(s\)|Job title|Organization|Role|Event|Award|Type|Skillset|Description\(s\).*|Affiliation/role|Organization/group|Position|Affiliation)", note):
            notes.append(note)
    return "; ".join(notes) if notes else None


def area_from_degree(degree: str) -> str:
    if " in " in degree:
        return degree.split(" in ", 1)[1].split(" and ", 1)[0].strip()
    return ""


def make_education(entry: dict[str, str], content: str, *, degree: str | None = None, date: str | None = None, display: DisplayConfig | None = None) -> Education:
    degree_text = degree if degree is not None else clean(entry["arg1"])[0]
    institution = clean(entry["arg2"])[0]
    location = clean(entry["arg3"])[0]
    start, end = split_dates(date if date is not None else entry["arg4"])
    details = clean(entry["arg5"])[0]
    return Education(
        institution=institution,
        degree=degree_text,
        area=area_from_degree(degree_text),
        start=start,
        end=end,
        location=location,
        advisor=None,
        details=none_if_empty(details),
        display=display or display_from_entry(entry, content),
        compact_override=None,
        notes=extract_entry_notes(entry.get("_raw", "")),
    )


def migrate_education() -> list[Education]:
    content = read_source(CV_DIR / "education.tex")
    entries = extract_cventry(content)
    if len(entries) < 2:
        warn("education.tex did not contain expected compact/full entries")
        return [make_education(entry, content) for entry in entries]

    compact_entry = entries[0]
    full_entry = entries[1]
    compact_display = display_from_entry(compact_entry, content)
    full_display = display_from_entry(full_entry, content)
    degree_parts = [part.strip() for part in full_entry["arg1"].split("\\linebreak") if part.strip()]
    date_parts = [part.strip() for part in full_entry["arg4"].split("\\linebreak") if part.strip()]

    migrated: list[Education] = []
    phd = make_education(
        full_entry,
        content,
        degree=clean(degree_parts[0] if degree_parts else full_entry["arg1"])[0],
        date=date_parts[0] if date_parts else full_entry["arg4"],
        display=full_display,
    )
    phd.compact_override = make_education(compact_entry, content, display=compact_display)
    migrated.append(phd)
    if len(degree_parts) > 1:
        migrated.append(
            make_education(
                full_entry,
                content,
                degree=clean(degree_parts[1])[0],
                date=date_parts[1] if len(date_parts) > 1 else full_entry["arg4"],
                display=full_display,
            )
        )
    for entry in entries[2:]:
        migrated.append(make_education(entry, content))
    return migrated


def make_experience(entry: dict[str, str], content: str) -> Experience:
    overrides: dict[str, str] = {}
    role = clean_field(entry["arg1"], "role", overrides)
    organization = clean_field(entry["arg2"], "organization", overrides)
    location = clean_field(entry["arg3"], "location", overrides)
    start, end = split_dates(entry["arg4"])
    body_text, body_override = clean(entry["arg5"])
    if body_override is not None:
        overrides["summary"] = body_override
    bullets = extract_bullets(entry["arg5"])
    summary = none_if_empty(body_text) if not bullets else None
    return Experience(
        organization=organization,
        role=role,
        start=start,
        end=end,
        location=location,
        summary=summary,
        bullets=bullets,
        display=display_from_entry(entry, content),
        notes=extract_entry_notes(entry.get("_raw", "")),
        latex_overrides=overrides or None,
    )


def migrate_experience(filename: str, *, expand_macros: bool = False) -> list[Experience]:
    content = read_source(CV_DIR / filename)
    if expand_macros:
        content = expand_local_macros(content, extract_local_macro_defs(content))
    return [make_experience(entry, content) for entry in extract_cventry(content)]


def split_skill_items(text: str) -> list[str]:
    items = [item.strip() for item in text.split(",") if item.strip()]
    return items or ([text] if text else [])


def migrate_skills(filename: str) -> list[Skill]:
    content = read_source(CV_DIR / filename)
    skills: list[Skill] = []
    for entry in extract_cvskill(content):
        overrides: dict[str, str] = {}
        category = clean_field(entry["arg1"], "category", overrides)
        description = clean_field(entry["arg2"], "items", overrides)
        skills.append(
            Skill(
                category=category,
                items=split_skill_items(description),
                display=display_from_entry(entry, content),
                latex_overrides=overrides or None,
            )
        )
    return skills


def migrate_projects() -> list[Project]:
    content = read_source(CV_DIR / "projects.tex")
    projects: list[Project] = []
    for entry in extract_cventry(content):
        overrides: dict[str, str] = {}
        role = clean_field(entry["arg1"], "summary", overrides)
        name = clean_field(entry["arg2"], "name", overrides)
        projects.append(
            Project(
                name=name,
                url=None,
                summary=none_if_empty(role),
                bullets=extract_bullets(entry["arg5"]),
                technologies=[],
                display=display_from_entry(entry, content),
                notes=extract_entry_notes(entry.get("_raw", "")),
                latex_overrides=overrides or None,
            )
        )
    return projects


def migrate_honors(filename: str) -> list[Honor]:
    content = read_source(CV_DIR / filename)
    return [
        Honor(
            title=clean(entry["arg1"])[0],
            issuer=none_if_empty(clean(entry["arg2"])[0]),
            location=none_if_empty(clean(entry["arg3"])[0]),
            date=none_if_empty(clean(entry["arg4"])[0]),
            summary=None,
            display=display_from_entry(entry, content),
            notes=extract_entry_notes(entry.get("_raw", "")),
        )
        for entry in extract_cvhonor(content)
    ]


def migrate_service() -> list[Service]:
    content = read_source(CV_DIR / "serviceleadership.tex")
    return [
        Service(
            role=clean(entry["arg1"])[0],
            organization=clean(entry["arg2"])[0],
            location=none_if_empty(clean(entry["arg3"])[0]),
            date=none_if_empty(clean(entry["arg4"])[0]),
            display=display_from_entry(entry, content),
            notes=extract_entry_notes(entry.get("_raw", "")),
        )
        for entry in extract_cvhonor(content)
    ]


def migrate_grants() -> list[Grant]:
    content = read_source(CV_DIR / "grants.tex")
    grants: list[Grant] = []
    for entry in extract_cventry(content):
        start, end = split_dates(entry["arg4"])
        grants.append(
            Grant(
                title=clean(entry["arg2"])[0],
                funder=clean(entry["arg3"])[0],
                role="Contributor",
                amount=none_if_empty(clean(entry["arg1"])[0]),
                start=none_if_empty(start),
                end=none_if_empty(end),
                details=extract_bullets(entry["arg5"]),
                display=display_from_entry(entry, content),
                notes=extract_entry_notes(entry.get("_raw", "")),
            )
        )
    return grants


def migrate_affiliations() -> list[Affiliation]:
    content = read_source(CV_DIR / "affiliations.tex")
    return [
        Affiliation(
            organization=clean(entry["arg2"])[0],
            role=none_if_empty(clean(entry["arg1"])[0]),
            date=none_if_empty(clean(entry["arg4"])[0]),
            display=display_from_entry(entry, content),
            notes=extract_entry_notes(entry.get("_raw", "")),
        )
        for entry in extract_cvhonor(content)
    ]


def migrate_summary() -> Summary | None:
    content = read_source(CV_DIR / "summary.tex")
    paragraph = extract_cvparagraph(content)
    if paragraph is None:
        return None
    text, _ = clean(paragraph)
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


def build_data() -> ProfessionalData:
    cv_tex = read_source(MYCV / "cv.tex")
    publication_keys = extract_cite_keys(MYCV / "Publications.bib")
    presentation_keys = extract_cite_keys(MYCV / "Presentations.bib")
    return ProfessionalData(
        schema_version="1.0",
        personal_info=make_personal_info(cv_tex),
        cv_config=CVConfig(citations_mode="selectedpubs", selected_publications=extract_selected_publications(cv_tex)),
        education=migrate_education(),
        research_experience=migrate_experience("researchexperience.tex", expand_macros=True),
        work_experience=migrate_experience("workexperience.tex"),
        skills=migrate_skills("skills.tex"),
        projects=migrate_projects(),
        honors=migrate_honors("honors.tex"),
        service_leadership=migrate_service(),
        teaching_experience=migrate_experience("teachingexperience.tex"),
        grants=migrate_grants(),
        extracurricular=migrate_experience("extracurricular.tex"),
        affiliations=migrate_affiliations(),
        wetlab_skills=migrate_skills("wetlabskills.tex"),
        summary=migrate_summary(),
        publications=[PublicationRef(cite_key=key) for key in publication_keys],
        presentations=[PresentationRef(cite_key=key) for key in presentation_keys],
    )


def write_yaml(data: ProfessionalData, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()  # pyright: ignore[reportUnknownVariableType]
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)  # pyright: ignore[reportUnknownMemberType]
    data_dict: dict[str, object] = data.model_dump(by_alias=False)
    with output_path.open("w") as handle:
        yaml.dump(data_dict, handle)  # pyright: ignore[reportUnknownMemberType]


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AwesomeCV LaTeX data to validated YAML.")
    _ = parser.add_argument("--output", default=str(ROOT / "data" / "professional.yaml"), help="Output YAML path")
    args: argparse.Namespace = parser.parse_args()

    data = build_data()
    output_path = Path(str(args.output))  # pyright: ignore[reportAny]
    write_yaml(data, output_path)
    print(f"Wrote {output_path}")
    counts = (
        f"Counts: education={len(data.education)}, research={len(data.research_experience)}, "
        f"work={len(data.work_experience)}, projects={len(data.projects)}, honors={len(data.honors)}, "
        f"publications={len(data.publications)}, presentations={len(data.presentations)}"
    )
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
