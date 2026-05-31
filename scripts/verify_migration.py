"""Automated completeness checker for migrated professional.yaml."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

from scripts.lib.bibtex_parser import extract_cite_keys
from scripts.lib.latex_parser import (
    extract_cventry,
    extract_cvhonor,
    extract_cvskill,
    extract_selected_publications,
)
from scripts.lib.schema import ProfessionalData

# Mapping of YAML section -> (tex filename, extraction function, macro type)
SECTION_SOURCE_MAP: dict[str, tuple[str, str]] = {
    "education": ("cv/education.tex", "cventry"),
    "research_experience": ("cv/researchexperience.tex", "cventry"),
    "work_experience": ("cv/workexperience.tex", "cventry"),
    "projects": ("cv/projects.tex", "cventry"),
    "teaching_experience": ("cv/teachingexperience.tex", "cventry"),
    "grants": ("cv/grants.tex", "cventry"),
    "extracurricular": ("cv/extracurricular.tex", "cventry"),
    "honors": ("cv/honors.tex", "cvhonor"),
    "service_leadership": ("cv/serviceleadership.tex", "cvhonor"),
    "affiliations": ("cv/affiliations.tex", "cvhonor"),
    "skills": ("cv/skills.tex", "cvskill"),
    "wetlab_skills": ("cv/wetlabskills.tex", "cvskill"),
}

# Sections with dual-variant that may reduce YAML count by 1
DUAL_VARIANT_SECTIONS = {"education"}


def load_yaml_data(yaml_path: Path) -> ProfessionalData:
    """Load and validate YAML file against schema."""
    yaml = YAML()
    data = yaml.load(yaml_path)
    return ProfessionalData.model_validate(data)


def count_source_entries(source_dir: Path, tex_file: str, macro_type: str) -> int:
    """Count entries in a source .tex file using the appropriate extractor."""
    path = source_dir / tex_file
    if not path.exists():
        return -1
    content = path.read_text()
    if macro_type == "cventry":
        return len(extract_cventry(content))
    elif macro_type == "cvhonor":
        return len(extract_cvhonor(content))
    elif macro_type == "cvskill":
        return len(extract_cvskill(content))
    return -1


def check_counts(prof: ProfessionalData, source_dir: Path) -> tuple[bool, str]:
    """Compare entry counts per section between source .tex files and YAML."""
    parts: list[str] = []
    failed = False

    for section, (tex_file, macro_type) in SECTION_SOURCE_MAP.items():
        source_count = count_source_entries(source_dir, tex_file, macro_type)
        if source_count < 0:
            parts.append(f"{section} source=? (file not found)")
            failed = True
            continue

        yaml_count = len(getattr(prof, section))

        # Allow dual-variant reduction
        allowed_reduction = 1 if section in DUAL_VARIANT_SECTIONS else 0
        min_expected = source_count - allowed_reduction

        if yaml_count < min_expected:
            parts.append(
                f"{section} source={source_count} yaml={yaml_count} "
                f"(MISSING {min_expected - yaml_count} ENTRY)"
            )
            failed = True
        elif section in DUAL_VARIANT_SECTIONS and yaml_count < source_count:
            parts.append(
                f"{section} source={source_count} yaml={yaml_count} "
                f"({source_count - yaml_count} dual-variant)"
            )
        else:
            parts.append(f"{section} source={source_count} yaml={yaml_count}")

    detail = " | ".join(parts)
    if failed:
        return False, f"✗ counts: {detail}"
    return True, f"✓ counts: {detail}"


def check_bib_completeness(
    prof: ProfessionalData, source_dir: Path
) -> tuple[bool, str]:
    """Verify all BibTeX keys present in YAML."""
    failed = False
    parts: list[str] = []

    # Publications
    pub_bib = source_dir / "Publications.bib"
    if pub_bib.exists():
        bib_keys = set(extract_cite_keys(pub_bib))
        yaml_keys = {p.cite_key for p in prof.publications}
        missing = bib_keys - yaml_keys
        parts.append(f"{len(yaml_keys)}/{len(bib_keys)} publications")
        if missing:
            parts[-1] += f" (missing: {', '.join(sorted(missing))})"
            failed = True
    else:
        parts.append("publications bib not found")
        failed = True

    # Presentations
    pres_bib = source_dir / "Presentations.bib"
    if pres_bib.exists():
        bib_keys = set(extract_cite_keys(pres_bib))
        yaml_keys = {p.cite_key for p in prof.presentations}
        missing = bib_keys - yaml_keys
        parts.append(f"{len(yaml_keys)}/{len(bib_keys)} presentations")
        if missing:
            parts[-1] += f" (missing: {', '.join(sorted(missing))})"
            failed = True
    else:
        parts.append("presentations bib not found")
        failed = True

    # Selected publications
    cv_tex = source_dir / "cv.tex"
    if cv_tex.exists():
        selected = extract_selected_publications(cv_tex.read_text())
        yaml_selected = prof.cv_config.selected_publications
        parts.append(f"{len(yaml_selected)}/{len(selected)} selected")
        if set(selected) != set(yaml_selected):
            missing_sel = set(selected) - set(yaml_selected)
            if missing_sel:
                parts[-1] += f" (missing: {', '.join(sorted(missing_sel))})"
            failed = True
    else:
        parts.append("cv.tex not found for selected")
        failed = True

    detail = ", ".join(parts)
    if failed:
        return False, f"✗ bib-completeness: {detail}"
    return True, f"✓ bib-completeness: {detail}"


def check_no_empty_sections(prof: ProfessionalData) -> tuple[bool, str]:
    """Every section must have ≥1 entry."""
    sections_to_check = [
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
    ]
    total = len(sections_to_check) + 1  # +1 for summary
    non_empty = 0
    empty_sections: list[str] = []

    for section in sections_to_check:
        entries = getattr(prof, section)
        if len(entries) > 0:
            non_empty += 1
        else:
            empty_sections.append(section)

    if prof.summary is not None:
        non_empty += 1
    else:
        empty_sections.append("summary")

    if empty_sections:
        return (
            False,
            f"✗ no-empty-sections: {non_empty}/{total} sections non-empty "
            f"(empty: {', '.join(empty_sections)})",
        )
    return True, f"✓ no-empty-sections: {total}/{total} sections non-empty"


def check_dual_variant(prof: ProfessionalData) -> tuple[bool, str]:
    """Verify education compact_override is present."""
    for edu in prof.education:
        if edu.compact_override is not None:
            return (
                True,
                f"✓ dual-variant: education compact_override present "
                f"({edu.degree} at {edu.institution})",
            )
    return False, "✗ dual-variant: no education entry has compact_override"


def check_selected_order(
    prof: ProfessionalData, source_dir: Path
) -> tuple[bool, str]:
    """Verify selected_publications matches exact order from cv.tex."""
    cv_tex = source_dir / "cv.tex"
    if not cv_tex.exists():
        return False, "✗ selected-order: cv.tex not found"

    source_keys = extract_selected_publications(cv_tex.read_text())
    yaml_keys = prof.cv_config.selected_publications

    if source_keys == yaml_keys:
        return True, f"✓ selected-order: {len(yaml_keys)} keys in correct order"

    if set(source_keys) != set(yaml_keys):
        missing = set(source_keys) - set(yaml_keys)
        extra = set(yaml_keys) - set(source_keys)
        detail = ""
        if missing:
            detail += f" missing: {', '.join(sorted(missing))}"
        if extra:
            detail += f" extra: {', '.join(sorted(extra))}"
        return False, f"✗ selected-order: key mismatch —{detail}"

    return (
        False,
        f"✗ selected-order: {len(yaml_keys)} keys present but order differs "
        f"(expected: {source_keys}, got: {yaml_keys})",
    )


def check_data_quality(prof: ProfessionalData) -> tuple[bool, str]:
    """Report potential issues as WARNINGS (never fails)."""
    warnings: list[str] = []

    def _check_field(section: str, index: int, field: str, value: str) -> None:
        # Raw LaTeX commands
        if re.search(r"\\[a-zA-Z]+", value):
            warnings.append(
                f"  {section}[{index}].{field}: possible raw LaTeX: "
                f"{value[:60]}..."
                if len(value) > 60
                else f"  {section}[{index}].{field}: possible raw LaTeX: {value}"
            )
        # Suspiciously short
        if len(value) < 3:
            warnings.append(
                f"  {section}[{index}].{field}: suspiciously short ({len(value)} chars): '{value}'"
            )

    def _check_str_fields(section: str, index: int, obj: object) -> None:
        for field_name in type(obj).__dict__.get("model_fields", {}):
            val = getattr(obj, field_name)
            if isinstance(val, str) and val:
                _check_field(section, index, field_name, val)
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    if isinstance(item, str) and item:
                        _check_field(section, index, f"{field_name}[{i}]", item)

    list_sections = [
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
    ]
    for section in list_sections:
        entries = getattr(prof, section)
        for i, entry in enumerate(entries):
            _check_str_fields(section, i, entry)

    if warnings:
        warning_text = "\n".join(warnings)
        return True, f"⚠ data-quality: {len(warnings)} warnings\n{warning_text}"
    return True, "⚠ data-quality: 0 warnings"


CHECK_MAP = {
    "counts": "check_counts",
    "bib-completeness": "check_bib_completeness",
    "no-empty-sections": "check_no_empty_sections",
    "dual-variant": "check_dual_variant",
    "selected-order": "check_selected_order",
    "data-quality": "check_data_quality",
}

ALL_CHECKS = [
    "counts",
    "bib-completeness",
    "no-empty-sections",
    "dual-variant",
    "selected-order",
    "data-quality",
]


def run_check(
    name: str, prof: ProfessionalData, source_dir: Path
) -> tuple[bool, str]:
    """Run a single named check."""
    if name == "counts":
        return check_counts(prof, source_dir)
    elif name == "bib-completeness":
        return check_bib_completeness(prof, source_dir)
    elif name == "no-empty-sections":
        return check_no_empty_sections(prof)
    elif name == "dual-variant":
        return check_dual_variant(prof)
    elif name == "selected-order":
        return check_selected_order(prof, source_dir)
    elif name == "data-quality":
        return check_data_quality(prof)
    else:
        return False, f"✗ Unknown check: {name}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify migrated professional.yaml against source files."
    )
    parser.add_argument(
        "--check",
        choices=[*ALL_CHECKS, "all"],
        default="all",
        help="Which check(s) to run (default: all)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("external/awesome-cv/mycv"),
        help="Path to CV source directory (default: external/awesome-cv/mycv/)",
    )
    parser.add_argument(
        "yaml_file",
        type=Path,
        help="Path to the professional.yaml file to verify",
    )
    args = parser.parse_args()

    yaml_path: Path = args.yaml_file
    source_dir: Path = args.source_dir

    if not yaml_path.exists():
        print(f"ERROR: YAML file not found: {yaml_path}", file=sys.stderr)
        return 1

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    print(f"Running verification checks on: {yaml_path}")
    print(f"Source directory: {source_dir}/")
    print()

    # Load and validate YAML
    try:
        prof = load_yaml_data(yaml_path)
    except Exception as e:
        print(f"ERROR: Failed to load/validate YAML: {e}", file=sys.stderr)
        return 1

    # Determine which checks to run
    checks = ALL_CHECKS if args.check == "all" else [args.check]

    failures = 0
    for check_name in checks:
        passed, message = run_check(check_name, prof, source_dir)
        print(message)
        if not passed and check_name != "data-quality":
            failures += 1

    print()
    if failures:
        print(f"RESULT: {failures} CHECK{'S' if failures > 1 else ''} FAILED")
        return 1
    else:
        print("RESULT: ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
