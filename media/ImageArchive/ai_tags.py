#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/ai_tags.py:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 4116a7f290719bee58c642175fec921b38c446e2 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-18 21:14:59 %
#  %ccm_git_file_name: ai_tags.py %
#  %ccm_git_path: media/ImageArchive/ai_tags.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 7268 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
import subprocess
import json
import base64
from pathlib import Path

PROMPT_FILE = str(Path.home() / "source/TermiteTowers/media/ImageArchive/prompts.txt")


# ------------------------------------------------------------
# 1. Read prompt blocks
# ------------------------------------------------------------
def _load_prompt_blocks():
    blocks = {}
    current = None
    section = None

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("=== model:"):
                model = line.split(":", 1)[1].strip().replace(" ===", "")
                current = {"prompt": [], "tags": [], "prkey": None}
                blocks[model] = current
                section = None
                continue

            if line.startswith("prkey:"):
                if current:
                    current["prkey"] = line.split(":", 1)[1].strip()
                continue

            if line.startswith("prompt:"):
                section = "prompt"
                continue

            if line.startswith("tags:"):
                section = "tags"
                continue

            if section == "prompt":
                current["prompt"].append(line)

            elif section == "tags":
                if line.strip():
                    current["tags"] = [t.strip() for t in line.split(",")]

    return blocks


PROMPT_BLOCKS = _load_prompt_blocks()


def route_model(filepath: str) -> str:
    """
    Decide which model to use for this image.
    Returns: "moondream", "llava-phi3", or "llava-next-34b"
    """

    # 1. If user explicitly requested a model → respect it
    if USER_OVERRIDE_MODEL:
        return USER_OVERRIDE_MODEL

    # 2. Stage 1: Moondream quick triage
    triage = run_moondream_triage(filepath)

    # triage is a dict:
    # {
    #   "scene_type": "church",
    #   "people_count": 1,
    #   "brightness": "dim",
    #   "objects": ["statue", "altar"]
    # }

    # 3. If Moondream fails → fallback to Phi3
    if not triage or "scene_type" not in triage:
        return "llava-phi3"

    people = triage.get("people_count", 0)
    scene  = triage.get("scene_type", "unknown")
    bright = triage.get("brightness", "normal")

    # 4. Simple scenes → Moondream is enough
    if people == 0 and scene in ("landscape", "street", "room"):
        return "moondream"

    # 5. Medium complexity → Phi3
    if people <= 1 and scene not in ("unknown", "complex"):
        return "llava-phi3"

    # 6. Low light + people → Phi3
    if bright in ("dark", "dim") and people <= 2:
        return "llava-phi3"

    # 7. Complex scenes → 34B
    if people > 2 or scene in ("church", "altar", "crowd", "complex"):
        return "llava-next-34b"

    # 8. Fallback
    return "llava-phi3"

# ------------------------------------------------------------
# 2. Select model → PR## → prompt
# ------------------------------------------------------------
def select_model(filepath: str) -> str:
    return route_model(filepath)


def get_pr_key(model: str) -> str:
    return PROMPT_BLOCKS[model]["prkey"]


def get_prompt(model: str) -> str:
    return "\n".join(PROMPT_BLOCKS[model]["prompt"]).strip()


def get_tags(model: str):
    return PROMPT_BLOCKS[model]["tags"]

def run_moondream_triage(filepath: str) -> dict:
    """
    Run Moondream triage using the PR01 strict JSON prompt.
    Returns a dict with keys:
      scene_type, indoor_outdoor, people_count, brightness, objects
    Returns {} on failure.
    """

    model = "moondream"
    pr_key = get_pr_key(model)
    prompt = get_prompt(model)

    # Base64 encode image
    try:
        with open(filepath, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return {}

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }

    # Call Ollama
    proc = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", json.dumps(payload)],
        capture_output=True
    )

    try:
        data = json.loads(proc.stdout.decode("utf-8"))
        raw = data.get("response", "").strip()
    except Exception:
        return {}

    # Parse the JSON Moondream returns
    try:
        triage = json.loads(raw)
        if isinstance(triage, dict):
            return triage
        return {}
    except Exception:
        return {}

def db_has_pr(cur, image_hash: str, pr_key: str) -> bool:
    """
    Return True if the DB already has aaAI:PR## tags for this image.
    """

    # 1. Find image_id
    cur.execute("SELECT id FROM image WHERE image_hash = %s", (image_hash,))
    row = cur.fetchone()
    if not row:
        return False
    image_id = row[0]

    # 2. Find tag_id for aaAI:PR##
    tag_key = f"aaAI:{pr_key}PromptResponse"
    cur.execute("SELECT id FROM tag_master WHERE tag_key = %s", (tag_key,))
    row = cur.fetchone()
    if not row:
        return False
    tag_id = row[0]

    # 3. Check image_tags
    cur.execute(
        "SELECT 1 FROM image_tags WHERE image_id = %s AND tag_id = %s",
        (image_id, tag_id)
    )
    if cur.fetchone():
        return True

    # 4. Check file_tags (staging)
    cur.execute(
        "SELECT 1 FROM file_tags WHERE image_id = %s AND tag_id = %s",
        (image_id, tag_id)
    )
    if cur.fetchone():
        return True

    return False

# ------------------------------------------------------------
# 3. Call Ollama
# ------------------------------------------------------------
def run_ollama(filepath: str, model: str, prompt: str) -> str:
    with open(filepath, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }

    proc = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", json.dumps(payload)],
        capture_output=True
    )

    try:
        data = json.loads(proc.stdout.decode("utf-8"))
        return data.get("response", "")
    except Exception:
        return ""


# ------------------------------------------------------------
# 4. AI version of get_all_tags()
# ------------------------------------------------------------
def ai_get_all_tags(filepath: str) -> dict:
    model = select_model(filepath)
    pr_key = get_pr_key(model)
    prompt = get_prompt(model)
    response = run_ollama(filepath, model, prompt)

    return {
        f"aaAI:{pr_key}ModelID": model,
        f"aaAI:{pr_key}PromptKey": pr_key,
        f"aaAI:{pr_key}PromptResponse": response
    }


# ------------------------------------------------------------
# 5. Optional: wrapper to replace ExifTool
# ------------------------------------------------------------
def get_all_tags(filepath: str) -> dict:
    # compute image hash
    image_hash = get_image_hash(filepath)

    # determine which PR## this image would use
    model = select_model(filepath)
    pr_key = get_pr_key(model)

    # check DB
    if db_has_pr(cur, image_hash, pr_key):
        return {}   # crawler will skip

    # otherwise generate AI tags
    return ai_get_all_tags(filepath)