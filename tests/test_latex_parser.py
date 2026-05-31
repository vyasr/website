from pathlib import Path

from scripts.lib.latex_parser import (
    determine_display_context,
    expand_local_macros,
    extract_comment_metadata,
    extract_cventry,
    extract_cvhonor,
    extract_cvparagraph,
    extract_cvskill,
    extract_local_macro_defs,
    extract_personal_info,
    extract_selected_publications,
    normalize_text,
)


ROOT = Path(__file__).resolve().parents[1]
CV_DIR = ROOT / "external" / "awesome-cv" / "mycv" / "cv"
MYCV_DIR = ROOT / "external" / "awesome-cv" / "mycv"


def read_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text()


def entry_lines_containing(all_lines: list[str], text: str) -> list[str]:
    start = next(index for index, line in enumerate(all_lines) if text in line)
    end = start
    seen_args = 0
    while end < len(all_lines) and seen_args < 5:
        seen_args += all_lines[end].count("{") - all_lines[end].count("\\{")
        end += 1
    return all_lines[start:end]


def test_extract_cventry_basic():
    entries = extract_cventry((CV_DIR / "workexperience.tex").read_text())

    assert entries[0]["arg1"].strip() == "Senior Software Engineer"
    assert entries[0]["arg2"].strip() == "NVIDIA"
    assert "Implemented critical algorithms" in entries[0]["arg5"]


def test_extract_cventry_multiline():
    entries = extract_cventry((CV_DIR / "education.tex").read_text())

    compact_phd = entries[0]
    assert compact_phd["arg1"].strip() == "Ph.D. in Chemical Engineering and Scientific Computing"
    assert compact_phd["arg4"].strip() == "2015 - 2020"
    assert compact_phd["arg5"].strip() == ""


def test_extract_cventry_nested_braces():
    tex = r"""
    \cventry
      {Role with {nested {braces}}}
      {Organization}
      {}
      {2020}
      {\begin{cvitems}\item {Nested item}\end{cvitems}}
    """

    entries = extract_cventry(tex)

    assert entries == [
        {
            "arg1": "Role with {nested {braces}}",
            "arg2": "Organization",
            "arg3": "",
            "arg4": "2020",
            "arg5": r"\begin{cvitems}\item {Nested item}\end{cvitems}",
            "_raw": entries[0]["_raw"],
        }
    ]


def test_extract_cvhonor_basic():
    entries = extract_cvhonor((CV_DIR / "honors.tex").read_text())

    assert entries[0]["arg1"].strip() == "Beyster Computational Innovation Fellow"
    assert entries[0]["arg2"].strip() == "University of Michigan"
    assert entries[0]["arg4"].strip() == "Jul 2019"


def test_extract_cvhonor_empty_arg():
    entries = extract_cvhonor((CV_DIR / "serviceleadership.tex").read_text())

    assert entries[0]["arg3"].strip() == ""


def test_extract_cvskill_basic():
    entries = extract_cvskill((CV_DIR / "skills.tex").read_text())

    assert entries[0]["arg1"].strip() == "Languages"
    assert "Python" in entries[0]["arg2"]
    assert len(entries) == 2


def test_extract_cvparagraph():
    paragraph = extract_cvparagraph((CV_DIR / "summary.tex").read_text())

    assert paragraph is not None
    assert paragraph.startswith("%---------------------------------------------------------")
    assert "I am a PhD candidate" in paragraph


def test_extract_personal_info():
    info = extract_personal_info((MYCV_DIR / "cv.tex").read_text())

    assert info["first_name"] == "Vyas"
    assert info["last_name"] == "Ramasubramani"
    assert info["email"] == "vyas.ramasubramani@gmail.com"
    assert info["homepage"] == "vyasr.com"
    assert info["github"] == "vyasr"
    assert info["linkedin"] == "vyas-ramasubramani"


def test_extract_selected_publications():
    keys = extract_selected_publications((MYCV_DIR / "cv.tex").read_text())

    assert keys == [
        "Ramasubramani2020b",
        "Ramasubramani2020",
        "Dice_2019",
        "simon2019",
        "vyas_ramasubramani-proc-scipy-2018",
        "adorf2018",
        "ADORF2018220",
        "Sinha:2014aa",
    ]


def test_display_context_outdated():
    all_lines = (CV_DIR / "workexperience.tex").read_text().splitlines()
    entry_lines = entry_lines_containing(all_lines, "Tutor")

    context = determine_display_context(entry_lines, all_lines)

    assert context == {"outdated": True, "extended": True, "compact": True}


def test_display_context_extended():
    all_lines = (CV_DIR / "projects.tex").read_text().splitlines()
    entry_lines = entry_lines_containing(all_lines, "rowan")

    context = determine_display_context(entry_lines, all_lines)

    assert context == {"outdated": False, "extended": True, "compact": True}


def test_display_context_none():
    all_lines = (CV_DIR / "workexperience.tex").read_text().splitlines()
    entry_lines = entry_lines_containing(all_lines, "Senior Software Engineer")

    context = determine_display_context(entry_lines, all_lines)

    assert context == {"outdated": False, "extended": True, "compact": True}


def test_dual_variant_education():
    content = (CV_DIR / "education.tex").read_text()
    entries = extract_cventry(content)
    all_lines = content.splitlines()

    compact_context = determine_display_context(entries[0]["_raw"].splitlines(), all_lines)
    full_context = determine_display_context(entries[1]["_raw"].splitlines(), all_lines)

    assert len(entries) == 6
    assert entries[0]["arg1"].strip() == "Ph.D. in Chemical Engineering and Scientific Computing"
    assert "M.S. in Chemical Engineering" in entries[1]["arg1"]
    assert compact_context["compact"] is True
    assert full_context["compact"] is False


def test_expand_local_macros():
    content = (CV_DIR / "researchexperience.tex").read_text()
    macros = extract_local_macro_defs(content)

    expanded = expand_local_macros(r"Antibiotics affect the \ecoli metabolome in \gal.", macros)

    assert expanded == "Antibiotics affect the E. coli metabolome in G. g. domesticus."


def test_extract_local_macro_defs():
    macros = extract_local_macro_defs((CV_DIR / "researchexperience.tex").read_text())

    assert macros["\\ecoli"] == r"\emph{E. coli }"
    assert macros["\\ejub"] == r"\emph{E. jubatus }"
    assert macros["\\gal"] == r"\emph{G. g. domesticus}"


def test_normalize_text_textsc():
    plain, override = normalize_text(r"Oct 2018 - \textsc{Present}")

    assert plain == "Oct 2018 - Present"
    assert override is None


def test_normalize_text_tiny_override():
    plain, override = normalize_text(r"signac framework ({\tiny github.com/glotzerlab/signac})")

    assert plain == "signac framework (github.com/glotzerlab/signac)"
    assert override == r"signac framework ({\tiny github.com/glotzerlab/signac})"


def test_extract_comment_metadata():
    line = r"    {Jan 2007 - Jun 2009} % (Captain: Jan 2007 - Jul 2007) % Date(s)"

    assert extract_comment_metadata(line) == "(Captain: Jan 2007 - Jul 2007) % Date(s)"
    assert extract_comment_metadata("%   ") is None
