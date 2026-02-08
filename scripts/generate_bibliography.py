#!/usr/bin/env python3
import argparse
import os
from pathlib import Path


MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def clean_text(value):
    if value is None:
        return ""
    return value.replace("{", "").replace("}", "").strip()


def month_value(value):
    if not value:
        return 0
    value = clean_text(value).strip().lower()
    if value.isdigit():
        return int(value)
    return MONTH_MAP.get(value, 0)


def parse_entries(text):
    entries = []
    length = len(text)
    i = 0
    while i < length:
        if text[i] != "@":
            i += 1
            continue
        i += 1
        start_type = i
        while i < length and text[i] not in "{(":
            i += 1
        entry_type = text[start_type:i].strip().lower()
        if i >= length:
            break
        opener = text[i]
        closer = "}" if opener == "{" else ")"
        i += 1
        start_body = i
        depth = 1
        while i < length and depth > 0:
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
            i += 1
        body = text[start_body : i - 1]
        key_end = body.find(",")
        if key_end == -1:
            continue
        key = body[:key_end].strip()
        fields_text = body[key_end + 1 :]
        fields = parse_fields(fields_text)
        fields["_type"] = entry_type
        fields["_key"] = key
        entries.append(fields)
    return entries


def parse_fields(text):
    fields = {}
    i = 0
    length = len(text)
    while i < length:
        while i < length and text[i] in " \t\n\r,":
            i += 1
        if i >= length:
            break
        start_name = i
        while i < length and text[i] not in "=\n\r":
            i += 1
        name = text[start_name:i].strip().lower()
        while i < length and text[i] != "=":
            i += 1
        if i >= length:
            break
        i += 1
        while i < length and text[i] in " \t\n\r":
            i += 1
        if i >= length:
            break
        if text[i] in "{\"":
            quote = text[i]
            i += 1
            depth = 1 if quote == "{" else 0
            start_value = i
            while i < length:
                char = text[i]
                if quote == "{":
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            break
                elif char == quote:
                    break
                i += 1
            value = text[start_value:i]
            i += 1
        else:
            start_value = i
            while i < length and text[i] not in ",\n\r":
                i += 1
            value = text[start_value:i]
        fields[name] = clean_text(value)
    return fields


def author_matches(author_field, allow_list):
    if not author_field:
        return False
    author_field = author_field.lower()
    return any(token.lower() in author_field for token in allow_list)


def entry_matches(entry, allow_types, allow_authors):
    if entry.get("_type") not in allow_types:
        return False
    author_field = entry.get("author") or entry.get("editor")
    return author_matches(author_field, allow_authors)


def entry_sort_key(entry):
    year = entry.get("year")
    try:
        year_value = int(year)
    except (TypeError, ValueError):
        year_value = 0
    month = month_value(entry.get("month"))
    return (year_value, month)


def pick_venue(entry):
    for field in ("journal", "booktitle", "organization", "series", "publisher"):
        value = entry.get(field)
        if value:
            return value
    return ""


def format_entry(entry):
    authors = clean_text(entry.get("author") or entry.get("editor") or "")
    title = clean_text(entry.get("title"))
    venue = clean_text(pick_venue(entry))
    year = clean_text(entry.get("year"))
    parts = []
    if authors:
        parts.append(authors.replace(" and ", ", "))
    if title:
        parts.append(f"\"{title}.\"")
    if venue:
        parts.append(venue)
    if year:
        parts.append(year)
    link = entry.get("doi") or entry.get("url") or entry.get("bdsk-url-1")
    if link:
        if link.startswith("10."):
            link = f"https://doi.org/{link}"
        parts.append(f"[link]({link})")
    return " ".join(parts).strip()


def group_entries(entries):
    grouped = {}
    for entry in entries:
        year = entry.get("year") or "Unknown"
        grouped.setdefault(year, []).append(entry)
    return grouped


def render_markdown(title, entries, note):
    lines = ["---", f"title: \"{title}\"", "hideTitle: true", "---", "", note, ""]
    grouped = group_entries(entries)
    years = sorted(grouped.keys(), key=lambda y: int(y) if y.isdigit() else 0, reverse=True)
    for year in years:
        lines.append(f"## {year}")
        lines.append("")
        for entry in grouped[year]:
            lines.append(f"- {format_entry(entry)}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_page(source_path, title, allow_types, allow_authors, output_path, note):
    text = Path(source_path).read_text(encoding="utf-8")
    entries = parse_entries(text)
    filtered = [entry for entry in entries if entry_matches(entry, allow_types, allow_authors)]
    filtered.sort(key=entry_sort_key, reverse=True)
    output = render_markdown(title, filtered, note)
    Path(output_path).write_text(output, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    cv_root = Path(args.cv_root)
    output_root = Path(args.output_root)

    publications_bib = cv_root / "mycv" / "Publications.bib"
    presentations_bib = cv_root / "mycv" / "Presentations.bib"

    allow_publications = {"article", "inproceedings"}
    allow_presentations = {"inproceedings", "conference"}

    publication_authors = [
        "Ramasubramani",
        "Adorf",
        "Dice",
        "Simon",
        "Glotzer",
        "Harper",
        "Spellings",
        "Dodd",
        "Karas",
        "Glaser",
        "Ettrich",
        "Sinha",
    ]
    presentation_authors = [
        "Ramasubramani",
        "Adorf",
        "Dice",
        "Simon",
        "Glotzer",
        "Harper",
        "Spellings",
        "Dodd",
        "Karas",
        "Glaser",
    ]

    note = "This page is generated from the CV bibliography. Do not edit manually."

    build_page(
        publications_bib,
        "Publications",
        allow_publications,
        publication_authors,
        output_root / "publications" / "index.md",
        note,
    )
    build_page(
        presentations_bib,
        "Presentations",
        allow_presentations,
        presentation_authors,
        output_root / "presentations" / "index.md",
        note,
    )


if __name__ == "__main__":
    main()
