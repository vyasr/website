#!/usr/bin/env python3
"""Post blog content to LinkedIn.

State model: .linkedin_state.json maps SHA256(filepath+body) → post_urn.
Idempotency: if hash is already in state, skip posting.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import cast

import frontmatter
import requests

LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"


def derive_slug(path: Path) -> str:
    """Derive URL slug from filename, stripping any YYYY-MM-DD- date prefix."""
    stem = path.stem
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)


def first_paragraph(content: str) -> str:
    """Extract the first non-empty paragraph from markdown content."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    return paragraphs[0] if paragraphs else ""


def content_hash(path: Path, body: str) -> str:
    """SHA256 of (str(path) + body) for idempotency."""
    h = hashlib.sha256()
    h.update((str(path) + body).encode("utf-8"))
    return h.hexdigest()


def load_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return cast(dict[str, str], json.load(f))


def save_state(path: Path, state: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        _ = f.write("\n")


def build_payload(author: str, url: str, title: str, summary: str) -> dict[str, object]:
    return {
        "author": author,
        "commentary": summary,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "lifecycleState": "PUBLISHED",
        "content": {
            "article": {
                "source": url,
                "title": title,
                "description": summary,
            }
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Post blog content to LinkedIn")
    _ = parser.add_argument("--content-file", required=True)
    _ = parser.add_argument("--dry-run", action="store_true")
    _ = parser.add_argument("--base-url", default="https://vyasr.com")
    _ = parser.add_argument("--state-file")
    args = parser.parse_args()

    content_path = Path(cast(str, args.content_file))
    post = frontmatter.load(content_path)

    if post.get("draft") is True:
        print("skipped: draft")
        return 0

    linkedin_value = post.get("linkedin")
    if not linkedin_value:
        print("skipped: no linkedin flag")
        return 0

    slug = post.get("slug") or derive_slug(content_path)
    base_url = cast(str, args.base_url).rstrip("/")
    article_url = f"{base_url}/blog/{slug}/"

    summary = linkedin_value if isinstance(linkedin_value, str) else first_paragraph(post.content)
    title = cast(str, post.get("title", ""))

    author = os.environ.get("LINKEDIN_AUTHOR_URN")
    if not author:
        print("ERROR: LINKEDIN_AUTHOR_URN is required", file=sys.stderr)
        return 3

    payload = build_payload(author, article_url, title, summary)

    state_file = cast(str | None, args.state_file)
    state_path = Path(state_file) if state_file else None
    digest = content_hash(content_path, post.content)

    if state_path:
        state = load_state(state_path)
        if digest in state:
            print("already posted, skipping")
            return 0
    else:
        state = None

    if cast(bool, args.dry_run):
        print(json.dumps(payload, indent=2))
        return 0

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        print("ERROR: LINKEDIN_ACCESS_TOKEN is required", file=sys.stderr)
        return 3

    response = requests.post(
        LINKEDIN_POSTS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Linkedin-Version": "202601",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code == 201:
        post_urn = response.headers.get("x-restli-id", "")
        print(post_urn)
        if state_path and state is not None:
            state[digest] = post_urn
            save_state(state_path, state)
        return 0

    if response.status_code == 401:
        print("ERROR: Token expired or invalid")
        return 1

    if response.status_code == 429:
        print("ERROR: Rate limited")
        return 2

    print(f"ERROR: {response.status_code} {response.text}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
