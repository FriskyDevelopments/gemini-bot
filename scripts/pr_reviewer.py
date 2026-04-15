#!/usr/bin/env python3
"""Autonomous PR reviewer: Groq (Llama 3.3) + PyGithub issue comment on the PR timeline."""

from __future__ import annotations

import json
import os
import sys
from typing import Final

import requests
from github import Auth, Github

SYSTEM_PROMPT: Final[str] = (
    "You are the Lead Systems Architect. Review this pull request for "
    "race conditions, unhandled exceptions, edge-case memory leaks, and general logic errors. "
    "Output your response as a concise markdown bulleted list of necessary changes. "
    "If no issues are found, simply state that the changes look solid."
)

GROQ_URL: Final[str] = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL: Final[str] = "llama-3.3-70b-versatile"
ALLOWED_SUFFIXES: Final[tuple[str, ...]] = (".py", ".ts", ".tsx")
# Groq context is large but keep a safety cap for huge PRs.
MAX_DIFF_CHARS: Final[int] = 100_000


def _env_required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return v


def _build_filtered_diff(pull) -> str:
    parts: list[str] = []
    for f in pull.get_files():
        name = f.filename or ""
        if not name.endswith(ALLOWED_SUFFIXES):
            continue
        patch = f.patch
        if not patch:
            continue
        parts.append(f"### {name}\n```diff\n{patch}\n```")
    return "\n\n".join(parts)


def _groq_review(diff_text: str, base_ref: str) -> str:
    key = _env_required("GROQ_API_KEY")
    user_content = (
        f"Target branch (merge base): `{base_ref}`\n\n"
        f"Unified diffs for changed `.py`, `.ts`, and `.tsx` files:\n\n{diff_text}"
    )
    r = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
        },
        timeout=120,
    )
    if not r.ok:
        print(r.text, file=sys.stderr)
        r.raise_for_status()
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        print(json.dumps(data, indent=2)[:4000], file=sys.stderr)
        raise RuntimeError("Unexpected Groq API response shape") from e


def main() -> None:
    # Skip review gracefully if Groq key is missing (e.g. on forks)
    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY not found; skipping AI PR review.")
        return

    token = _env_required("GITHUB_TOKEN")
    repo_name = _env_required("GITHUB_REPOSITORY")
    pr_number = int(_env_required("PR_NUMBER"))
    base_ref = os.environ.get("PR_BASE_REF", "")

    g = Github(auth=Auth.Token(token))
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    diff_text = _build_filtered_diff(pr)
    if not diff_text:
        pr.create_issue_comment(
            "**AI PR Reviewer** — No `.py`, `.ts`, or `.tsx` file changes with a retrievable "
            "patch in this PR; skipping model review."
        )
        return

    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = (
            diff_text[:MAX_DIFF_CHARS]
            + "\n\n_(Diff truncated for review; focus on the above.)_"
        )

    review_body = _groq_review(diff_text, base_ref)
    comment = (
        "## AI PR Review (Groq — Lead Systems Architect)\n\n"
        + review_body
    )
    pr.create_issue_comment(comment)


if __name__ == "__main__":
    main()
