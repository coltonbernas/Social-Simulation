"""Chat model for the simulation guide.

Uses an OpenAI API key from the environment or a project .env file when one
is present. Otherwise it falls back to Pollinations' free model.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4.1-mini"
FREE_URL = "https://text.pollinations.ai/openai/chat/completions"
FREE_MODEL = "openai-fast"


class ModelError(Exception):
    """The model did not return a reply."""


def _load_dotenv():
    root = Path(__file__).resolve().parents[2]
    for path in (root / ".env", root / "pythonFiles" / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def using_openai():
    _load_dotenv()
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def active_model():
    if using_openai():
        return os.environ.get("OPENAI_MODEL", "").strip() or OPENAI_MODEL
    return FREE_MODEL


def complete(messages, timeout=45):
    """Send a chat and return the assistant text."""
    _load_dotenv()
    if using_openai():
        return _post(
            OPENAI_URL,
            messages,
            active_model(),
            timeout,
            headers={"Authorization": "Bearer {}".format(os.environ["OPENAI_API_KEY"].strip())},
            label="OpenAI",
        )
    return _post(
        FREE_URL,
        messages,
        FREE_MODEL,
        timeout,
        headers={"Referer": "https://pollinations.ai"},
        label="free model",
    )


def _post(url, messages, model, timeout, headers, label):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.4,
    }).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "SocialSimulationGuide/1.0",
    }
    request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        if label == "free model" and error.code == 402:
            raise ModelError(
                "The free model is at its limit for this address. "
                "It allows about one reply every 30 seconds."
            )
        raise ModelError("{} returned HTTP {}. {}".format(label, error.code, detail[:180]))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ModelError("{} could not be reached ({})".format(label, error))

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ModelError("{} returned an unexpected reply.".format(label))
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    text = str(content).strip()
    if not text:
        raise ModelError("{} returned an empty reply.".format(label))
    return text
