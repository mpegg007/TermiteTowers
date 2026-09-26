#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: util/extract-cline-history.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 332e1344949643e3641133d9b90e01a19d01a4d6 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-08-14 18:06:37 %
#  %ccm_git_file_name: extract-cline-history.py %
#  %ccm_git_path: util/extract-cline-history.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 6019 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""Extract clean prompt -> final-answer pairs from local Cline/claude-dev history.

Cline stores task history in VS Code global storage. This walks that directory
and, for every task, pulls out:

  prompt  = the initial user task  (ui_messages.json entry with say == "task")
  answer  = the final DeepSeek response (last say == "completion_result" entry)

The output is JSONL, one record per task, ready to replay `prompt` against
local Ollama models and compare against `answer` (DeepSeek's reference output).

Usage:
    python3 util/extract-cline-history.py [--out cline_history.jsonl] [--tasks DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

# Older Cline was published as "claude-dev"; newer builds use "cline".
# Check both under the user's VS Code global storage.
CANDIDATE_DIRS = [
    "~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/tasks",
    "~/.config/Code/User/globalStorage/saoudrizwan.cline/tasks",
    "~/.vscode/globalStorage/saoudrizwan.claude-dev/tasks",
    "~/.vscode/globalStorage/saoudrizwan.cline/tasks",
]


def _first_text(content) -> str:
    """Flatten an OpenAI-style content blob (str or list of parts) to text."""
    if isinstance(content, str):
        return content
    parts = []
    if isinstance(content, list):
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
            elif isinstance(p, str):
                parts.append(p)
    return "\n".join(parts).strip()


def _extract_from_ui(ui_path: Path) -> dict:
    """Extract prompt/answer/model from ui_messages.json."""
    ui = json.loads(ui_path.read_text(encoding="utf-8"))
    prompt = ""
    answers = []
    model = provider = None

    for m in ui:
        say = m.get("say")
        text = (m.get("text") or "").strip()
        if say == "task" and not prompt:
            prompt = text
        elif say == "completion_result" and text:
            answers.append(text)
        # modelInfo appears on assistant/reasoning messages
        mi = m.get("modelInfo")
        if mi and not model:
            model = mi.get("modelId") or mi.get("model")
            provider = mi.get("providerId") or mi.get("provider")

    return {
        "prompt": prompt,
        "answer": answers[-1] if answers else "",
        "all_answers": answers,
        "model": model,
        "provider": provider,
    }


def _extract_from_api(api_path: Path) -> dict:
    """Fallback: pull <task> from the first user message of api_conversation_history.json."""
    conv = json.loads(api_path.read_text(encoding="utf-8"))
    prompt = ""
    model = provider = None
    for m in conv:
        if m.get("role") == "user" and not prompt:
            text = _first_text(m.get("content"))
            start = text.find("<task>")
            end = text.find("</task>")
            if start != -1 and end != -1:
                prompt = text[start + len("<task>"):end].strip()
        mi = m.get("modelInfo")
        if mi and not model:
            model = mi.get("modelId") or mi.get("model")
            provider = mi.get("providerId") or mi.get("provider")
    return {"prompt": prompt, "answer": "", "all_answers": [], "model": model, "provider": provider}


def discover_tasks_dir(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_dir() else None
    for cand in CANDIDATE_DIRS:
        p = Path(cand).expanduser()
        if p.is_dir():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cline_history.jsonl")
    ap.add_argument("--tasks", default=None, help="override tasks dir")
    args = ap.parse_args()

    tasks_dir = discover_tasks_dir(args.tasks)
    if tasks_dir is None:
        print("Could not find Cline tasks directory. Pass --tasks explicitly.", file=sys.stderr)
        return 1

    out_path = Path(args.out).expanduser()
    records = []
    skipped = 0

    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        ui_path = task_dir / "ui_messages.json"
        api_path = task_dir / "api_conversation_history.json"

        if ui_path.exists():
            data = _extract_from_ui(ui_path)
        elif api_path.exists():
            data = _extract_from_api(api_path)
        else:
            skipped += 1
            continue

        if not data["prompt"]:
            skipped += 1
            continue

        # Task dir name is a millisecond epoch timestamp.
        try:
            ts = int(task_dir.name) / 1000
            date = dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds")
        except ValueError:
            ts = 0.0
            date = ""

        records.append(
            {
                "id": task_dir.name,
                "date": date,
                "ts": ts,
                "model": data["model"],
                "provider": data["provider"],
                "prompt": data["prompt"],
                "answer": data["answer"],
                "num_completions": len(data["all_answers"]),
            }
        )

    records.sort(key=lambda r: r["ts"])
    with out_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    models = sorted({f"{r['provider']}/{r['model']}" for r in records})
    with_answers = sum(1 for r in records if r["answer"])
    print(f"Tasks dir : {tasks_dir}")
    print(f"Records   : {len(records)} written to {out_path}")
    print(f"Skipped   : {skipped} (no prompt found)")
    print(f"With final answer: {with_answers}")
    print(f"Models    : {', '.join(models) or '(unknown)'}")
    if records:
        print(f"Date range: {records[0]['date']} -> {records[-1]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
