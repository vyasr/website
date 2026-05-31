from __future__ import annotations

import re


def _parse_brace_args_with_end(text: str, n: int, start_pos: int) -> tuple[list[str], int]:
    args: list[str] = []
    pos = start_pos
    while len(args) < n:
        pos = _skip_space_and_comments(text, pos)
        if pos >= len(text) or text[pos] != "{":
            break

        pos += 1
        depth = 1
        arg_start = pos
        while pos < len(text) and depth > 0:
            if text[pos] == "\\":
                pos += 2
                continue
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
            pos += 1

        if depth != 0:
            break
        args.append(text[arg_start : pos - 1])

    return args, pos


def _skip_space_and_comments(text: str, pos: int) -> int:
    while pos < len(text):
        if text[pos] in " \t\n\r":
            pos += 1
        elif text[pos] == "%":
            newline = text.find("\n", pos)
            pos = len(text) if newline == -1 else newline + 1
        else:
            break
    return pos


def _parse_brace_args(text: str, n: int, start_pos: int) -> list[str]:
    return _parse_brace_args_with_end(text, n, start_pos)[0]


def _extract_macro_entries(tex_content: str, macro_name: str, arg_count: int) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    needle = f"\\{macro_name}"
    pos = 0
    while True:
        start = tex_content.find(needle, pos)
        if start == -1:
            break
        after = start + len(needle)
        if after < len(tex_content) and (tex_content[after].isalpha() or tex_content[after] == "*"):
            pos = after
            continue

        args, end = _parse_brace_args_with_end(tex_content, arg_count, after)
        if len(args) == arg_count:
            entry: dict[str, str] = {f"arg{i + 1}": arg for i, arg in enumerate(args)}
            entry["_raw"] = tex_content[start:end]
            entries.append(entry)
            pos = end
        else:
            pos = after
    return entries


def extract_cventry(tex_content: str) -> list[dict[str, str]]:
    return _extract_macro_entries(tex_content, "cventry", 5)


def extract_cvhonor(tex_content: str) -> list[dict[str, str]]:
    return _extract_macro_entries(tex_content, "cvhonor", 4)


def extract_cvskill(tex_content: str) -> list[dict[str, str]]:
    return _extract_macro_entries(tex_content, "cvskill", 2)


def extract_cvparagraph(tex_content: str) -> str | None:
    begin = "\\begin{cvparagraph}"
    end = "\\end{cvparagraph}"
    start = tex_content.find(begin)
    if start == -1:
        return None
    content_start = start + len(begin)
    content_end = tex_content.find(end, content_start)
    if content_end == -1:
        return None
    return tex_content[content_start:content_end].strip()


def extract_personal_info(tex_content: str) -> dict[str, str]:
    info: dict[str, str] = {}
    name_pos = tex_content.find("\\name")
    if name_pos != -1:
        args = _parse_brace_args(tex_content, 2, name_pos + len("\\name"))
        if len(args) == 2:
            info["first_name"] = args[0].strip()
            info["last_name"] = args[1].strip()
            info["name"] = f"{args[0].strip()} {args[1].strip()}".strip()

    for macro in ("mobile", "email", "homepage", "github", "linkedin", "gitlab"):
        pos = tex_content.find(f"\\{macro}")
        if pos == -1:
            continue
        args = _parse_brace_args(tex_content, 1, pos + len(macro) + 1)
        if args:
            info[macro] = args[0].strip()

    pos = tex_content.find("\\stackexchange")
    if pos != -1:
        args = _parse_brace_args(tex_content, 2, pos + len("\\stackexchange"))
        if len(args) == 2:
            info["stackexchange_id"] = args[0].strip()
            info["stackexchange_name"] = args[1].strip()

    pos = tex_content.find("\\googlescholar")
    if pos != -1:
        args = _parse_brace_args(tex_content, 2, pos + len("\\googlescholar"))
        if len(args) == 2:
            info["googlescholar_id"] = args[0].strip()
            info["googlescholar_name"] = args[1].strip()

    return info


def extract_selected_publications(tex_content: str) -> list[str]:
    marker = "\\newcommand*{\\selectedpublications}"
    pos = tex_content.find(marker)
    start_pos = pos + len(marker) if pos != -1 else -1
    if pos == -1:
        pos = tex_content.find("\\selectedpublications")
        start_pos = pos + len("\\selectedpublications") if pos != -1 else -1
    if start_pos == -1:
        return []
    args = _parse_brace_args(tex_content, 1, start_pos)
    if not args:
        return []
    return [key.strip() for key in args[0].split(",") if key.strip()]


def determine_display_context(entry_lines: list[str], all_lines: list[str]) -> dict[str, bool]:
    normalized_entry_lines = [line.strip() for line in entry_lines if line.strip()]
    entry_index = -1
    for idx in range(len(all_lines) - len(normalized_entry_lines) + 1):
        candidate = [line.strip() for line in all_lines[idx : idx + len(normalized_entry_lines)] if line.strip()]
        if candidate == normalized_entry_lines:
            entry_index = idx
            break

    if entry_index == -1:
        for idx, line in enumerate(all_lines):
            if normalized_entry_lines and line.strip() == normalized_entry_lines[0]:
                entry_index = idx
                break

    if entry_index == -1:
        entry_index = len(all_lines)

    stack: list[tuple[str, bool]] = []
    for line in all_lines[: max(entry_index, 0)]:
        stripped = line.strip()
        if stripped.startswith("\\ifoutdated"):
            stack.append(("outdated", False))
        elif stripped.startswith("\\ifextended"):
            stack.append(("extended", False))
        elif stripped.startswith("\\ifcompact"):
            stack.append(("compact", False))
        elif stripped.startswith("\\else") and stack:
            name, _ = stack[-1]
            stack[-1] = (name, True)
        elif stripped.startswith("\\fi") and stack:
            _ = stack.pop()

    context = {"outdated": False, "extended": True, "compact": True}
    for name, in_else in stack:
        if name == "outdated" and not in_else:
            context["outdated"] = True
        elif name == "extended":
            context["extended"] = not in_else
        elif name == "compact":
            context["compact"] = not in_else
    return context


def extract_local_macro_defs(tex_content: str) -> dict[str, str]:
    macros: dict[str, str] = {}
    pos = 0
    for command in ("\\newcommand*", "\\newcommand"):
        pos = 0
        while True:
            start = tex_content.find(command, pos)
            if start == -1:
                break
            args, end = _parse_brace_args_with_end(tex_content, 2, start + len(command))
            if len(args) == 2 and args[0].strip().startswith("\\"):
                macros[args[0].strip()] = args[1]
            pos = end if end > start else start + len(command)
    return macros


def expand_local_macros(tex_content: str, macros: dict[str, str]) -> str:
    expanded = tex_content
    for macro, replacement in sorted(macros.items(), key=lambda item: len(item[0]), reverse=True):
        plain, _ = normalize_text(replacement)
        expanded = re.sub(rf"{re.escape(macro)}(?![A-Za-z])", plain, expanded)
    return expanded


def normalize_text(latex_str: str) -> tuple[str, str | None]:
    original = latex_str
    text = latex_str.strip()
    latex_override: str | None = None

    if re.search(r"\\tiny\b|\\scriptsize\b|\\fontsize\b", text):
        latex_override = original

    text = text.replace("\\linebreak", " ")
    text = text.replace("~~", " ")
    text = text.replace("\\&", "&")
    text = text.replace("\\%", "%")
    text = text.replace("\\$", "$")
    text = text.replace("\\#", "#")
    text = text.replace("\\_", "_")
    text = text.replace("\\textasciitilde{}", "~")
    text = text.replace("\\quad", " ")

    for command in ("textsc", "emph", "textbf", "textit", "textnormal", "textsuperscript"):
        text = _replace_one_arg_command(text, command)

    text = re.sub(r"\{\\(?:tiny|scriptsize)\s+([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:tiny|scriptsize)\s*", "", text)
    text = re.sub(r"\\[,;:! ]", " ", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*", " ", text)
    return text.strip(), latex_override


def _replace_one_arg_command(text: str, command: str) -> str:
    needle = f"\\{command}"
    pos = 0
    result = ""
    while True:
        start = text.find(needle, pos)
        if start == -1:
            result += text[pos:]
            break
        result += text[pos:start]
        args, end = _parse_brace_args_with_end(text, 1, start + len(needle))
        if args:
            result += args[0]
            pos = end
        else:
            result += needle
            pos = start + len(needle)
    return result


def extract_comment_metadata(line: str) -> str | None:
    escaped = False
    for idx, char in enumerate(line):
        if char == "\\" and not escaped:
            escaped = True
            continue
        if char == "%" and not escaped:
            comment = line[idx + 1 :].strip()
            if not comment:
                return None
            if re.fullmatch(r"[-\s]+", comment):
                return None
            return comment
        escaped = False
    return None
