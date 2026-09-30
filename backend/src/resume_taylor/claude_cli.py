"""Running the Claude Code CLI as a pure text-generation step (`claude -p`, no tools,
scrubbed environment, cwd outside this repo)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from .config import CLAUDE_TIMEOUT, EFFORT, MODEL


def claude_path() -> str | None:
    """Where the `claude` CLI is on PATH, or None."""
    return shutil.which("claude")


def find_claude_cli() -> str:
    claude_bin = claude_path()
    if not claude_bin:
        sys.exit(
            "Could not find the `claude` CLI on PATH. Install the Claude Code CLI "
            "and run `claude /login` to authenticate with your subscription."
        )
    return claude_bin


def clean_subprocess_env() -> dict:
    # Strip inherited CLAUDE_*/ANTHROPIC_* vars (e.g. this script may itself be
    # run from inside a Claude Code session) so the child CLI call behaves like
    # a clean, standalone invocation rather than a nested session — otherwise
    # it starts narrating/asking follow-up questions like an interactive agent.
    # The one exception is ANTHROPIC_API_KEY, which the user set on purpose
    # (in .env or the app's Settings) to pay per use instead of using a login.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().startswith("CLAUDE") and not k.upper().startswith("ANTHROPIC")
    }
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        env["ANTHROPIC_API_KEY"] = key
    return env


def invoke_claude(
    claude_bin: str,
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    effort: str | None = None,
) -> str:
    # Pass the system prompt via a file, not a CLI arg: the `claude` entry on
    # Windows is a .CMD shim run through cmd.exe, which caps the whole command
    # line at 8191 chars, so a long system prompt overflows it ("The command
    # line is too long."). --system-prompt-file has no such limit.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="utf-8", delete=False
    ) as sp_file:
        sp_file.write(system_prompt)
        sp_path = sp_file.name

    try:
        proc = subprocess.run(
            [
                claude_bin,
                "-p",
                "--output-format",
                "json",
                "--tools",
                "",
                "--model",
                model or MODEL,
                "--effort",
                effort or EFFORT,
                "--system-prompt-file",
                sp_path,
            ],
            input=user_message,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=clean_subprocess_env(),
            cwd=tempfile.gettempdir(),  # avoid CLAUDE.md auto-discovery from this repo's cwd
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        sys.exit(
            f"claude CLI did not respond within {CLAUDE_TIMEOUT}s. Re-run, or raise "
            "CLAUDE_TIMEOUT in .env."
        )
    finally:
        os.unlink(sp_path)

    if proc.returncode != 0:
        sys.exit(f"claude CLI exited with an error:\n{proc.stderr.strip()}")

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"Could not parse claude CLI output as JSON ({exc}):\n{proc.stdout}")

    if envelope.get("is_error"):
        sys.exit(f"claude CLI reported an error: {envelope.get('result')}")

    return envelope.get("result", "")


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text
