"""Local-first inference client for the Scientific Question Compiler.

Talks to a user-owned OpenAI-compatible server (Ornith-35B-Q4_K_M via llama.cpp
on :8080) using only the Python standard library — no cloud, no API keys, no
third-party HTTP deps.

Key lessons baked in from prior builds:
- The reasoning model emits a long Chain-of-Thought trace (in `reasoning_content`)
  BEFORE the answer. So we request a large `max_tokens` (KC_MAX_TOKENS, default
  12000) or the answer comes back empty.
- The server can be laggy on the first token; we probe with a tiny request and
  retry before each real call.
- Model output drifts from schema; callers must validate/repair. We only extract
  the first balanced JSON object from the response (CoT-safe).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error

DEFAULT_PORT = int(os.environ.get("KC_PORT", "8080"))
DEFAULT_MODEL = os.environ.get("KC_MODEL", "local-model")
MAX_TOKENS = int(os.environ.get("KC_MAX_TOKENS", "12000"))
TIMEOUT = int(os.environ.get("KC_TIMEOUT", "600"))
PROBE_TOKENS = int(os.environ.get("KC_PROBE_TOKENS", "1"))
PROBE_TRIES = int(os.environ.get("KC_PROBE_TRIES", "6"))
PROBE_SLEEP = float(os.environ.get("KC_PROBE_SLEEP", "2.0"))


def _url(port: int = DEFAULT_PORT) -> str:
    return f"http://localhost:{port}/v1/chat/completions"


def _post(payload: dict, timeout: int) -> dict | None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _url(), data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  [post] error: {exc}")
        return None


def probe(port: int = DEFAULT_PORT) -> bool:
    """Lightweight connectivity/speed check: ask for one token."""
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": PROBE_TOKENS,
        "temperature": 0,
    }
    for attempt in range(1, PROBE_TRIES + 1):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    _url(port),
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=15,
            ) as resp:
                json.loads(resp.read().decode())
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"  [probe] attempt {attempt} failed: {exc}")
            time.sleep(PROBE_SLEEP)
    return False


def complete_json(
    system: str,
    user: str,
    port: int = DEFAULT_PORT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
    temperature: float = 0.2,
) -> dict:
    """Call the model and parse a single JSON object from the response.

    Returns {} on repeated failure (callers must validate/repair downstream).
    """
    if not probe(port):
        raise RuntimeError("local inference server not reachable after retries")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    for attempt in range(1, 4):
        resp = _post(payload, timeout=TIMEOUT)
        if not resp:
            time.sleep(PROBE_SLEEP * attempt)
            continue
        content = (resp.get("choices", [{}])[0]
                   .get("message", {}).get("content", "") or "")
        parsed = _extract_json(content)
        if parsed:
            return parsed
        print(f"  [complete_json] attempt {attempt}: no JSON extracted")
    return {}


def _extract_json(content: str) -> dict:
    """Pull the first balanced {...} object out of a model response (CoT-safe)."""
    start = content.find("{")
    if start == -1:
        return {}
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(content)):
        c = content[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                blob = content[start : i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    return {}
    return {}


if __name__ == "__main__":
    print("probe:", probe())
    print("test:", complete_json(
        "You are a JSON emitter. Reply with ONLY a JSON object, no prose.",
        'Return JSON: {"ok": true, "n": 3}',
    ))
