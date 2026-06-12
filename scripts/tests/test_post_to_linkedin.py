"""Unit tests for post_to_linkedin.py."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import responses as responses_lib

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = Path(__file__).parent.parent / "post_to_linkedin.py"

# Add scripts/ to path so we can import the module directly for API tests
sys.path.insert(0, str(SCRIPT.parent))
import post_to_linkedin  # noqa: E402


def run_script(*args, env_extra=None):
    env = {**os.environ, "LINKEDIN_AUTHOR_URN": "urn:li:person:testuser"}
    # Remove token by default so tests don't accidentally call APIs
    env.pop("LINKEDIN_ACCESS_TOKEN", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _compute_hash(path: Path) -> str:
    """Mirror the content_hash logic from the script."""
    import frontmatter

    post = frontmatter.load(path)
    h = hashlib.sha256()
    h.update((str(path) + post.content).encode("utf-8"))
    return h.hexdigest()


def _run_main(*args, env_vars=None):
    """Run main() in-process with patched sys.argv and env."""
    argv = ["post_to_linkedin.py", *args]
    env = {"LINKEDIN_AUTHOR_URN": "urn:li:person:testuser"}
    if env_vars:
        env.update(env_vars)
    with patch.object(sys, "argv", argv), patch.dict(os.environ, env, clear=False):
        return post_to_linkedin.main()


# --- Dry-run tests (subprocess-based) ---


def test_dry_run_blog_post():
    result = run_script("--content-file", str(FIXTURES / "blog_post.md"), "--dry-run")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["content"]["article"]["source"] == "https://vyasr.com/blog/test-blog-post/"
    assert payload["content"]["article"]["title"] == "Test Blog Post"


def test_dry_run_uses_slug_from_front_matter():
    result = run_script("--content-file", str(FIXTURES / "blog_post.md"), "--dry-run")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "/blog/test-blog-post/" in payload["content"]["article"]["source"]


def test_draft_skipped():
    result = run_script("--content-file", str(FIXTURES / "draft_post.md"), "--dry-run")
    assert result.returncode == 0
    assert "skipped: draft" in result.stdout


def test_no_linkedin_flag_skipped():
    result = run_script("--content-file", str(FIXTURES / "no_linkedin.md"), "--dry-run")
    assert result.returncode == 0
    assert "skipped: no linkedin flag" in result.stdout


def test_custom_summary_string():
    result = run_script("--content-file", str(FIXTURES / "custom_summary.md"), "--dry-run")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["commentary"] == "This is a custom LinkedIn summary."
    assert payload["content"]["article"]["description"] == "This is a custom LinkedIn summary."


# --- API response tests (in-process with responses mock) ---


@responses_lib.activate
def test_api_201_success(tmp_path):
    responses_lib.add(
        responses_lib.POST,
        "https://api.linkedin.com/rest/posts",
        status=201,
        headers={"x-restli-id": "urn:li:share:123456"},
    )
    rc = _run_main(
        "--content-file", str(FIXTURES / "blog_post.md"),
        "--state-file", str(tmp_path / "state.json"),
        env_vars={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert rc == 0


@responses_lib.activate
def test_api_401_unauthorized(tmp_path):
    responses_lib.add(
        responses_lib.POST,
        "https://api.linkedin.com/rest/posts",
        status=401,
        json={"message": "unauthorized"},
    )
    rc = _run_main(
        "--content-file", str(FIXTURES / "blog_post.md"),
        "--state-file", str(tmp_path / "state.json"),
        env_vars={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert rc == 1


@responses_lib.activate
def test_api_429_rate_limited(tmp_path):
    responses_lib.add(
        responses_lib.POST,
        "https://api.linkedin.com/rest/posts",
        status=429,
        json={"message": "rate limited"},
    )
    rc = _run_main(
        "--content-file", str(FIXTURES / "blog_post.md"),
        "--state-file", str(tmp_path / "state.json"),
        env_vars={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert rc == 2


@responses_lib.activate
def test_api_500_server_error(tmp_path):
    responses_lib.add(
        responses_lib.POST,
        "https://api.linkedin.com/rest/posts",
        status=500,
        json={"message": "internal error"},
    )
    rc = _run_main(
        "--content-file", str(FIXTURES / "blog_post.md"),
        "--state-file", str(tmp_path / "state.json"),
        env_vars={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert rc == 3


# --- State file tests ---


def test_state_file_prevents_duplicate(tmp_path):
    fixture = FIXTURES / "blog_post.md"
    digest = _compute_hash(fixture)
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({digest: "urn:li:share:existing"}))

    result = run_script(
        "--content-file",
        str(fixture),
        "--state-file",
        str(state_file),
        env_extra={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert result.returncode == 0
    assert "already posted, skipping" in result.stdout


@responses_lib.activate
def test_state_file_written_on_success(tmp_path):
    responses_lib.add(
        responses_lib.POST,
        "https://api.linkedin.com/rest/posts",
        status=201,
        headers={"x-restli-id": "urn:li:share:789"},
    )
    state_file = tmp_path / "state.json"
    fixture = FIXTURES / "blog_post.md"

    rc = _run_main(
        "--content-file", str(fixture),
        "--state-file", str(state_file),
        env_vars={"LINKEDIN_ACCESS_TOKEN": "fake_token"},
    )
    assert rc == 0

    state = json.loads(state_file.read_text())
    digest = _compute_hash(fixture)
    assert state[digest] == "urn:li:share:789"
