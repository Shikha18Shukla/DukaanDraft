"""Ollama integration for DukaanDraft.

Talks only to the local Ollama HTTP API. Contains no cloud inference calls,
never downloads models, and never starts a second Ollama server.

Generation uses a single non-streaming request with JSON output format. If
the model returns malformed or schema-invalid output, the request is retried
once (two attempts total, never more) before giving up.
"""

import json
import socket
import urllib.error
import urllib.request

HEALTH_TIMEOUT = 5

# Maximum generation attempts: the initial request plus one bounded retry.
MAX_ATTEMPTS = 2

REQUIRED_TEXT_FIELDS = (
    "product_title",
    "whatsapp_message",
    "product_description",
    "cta_suggestion",
    "marketplace_title",
)

MAX_HASHTAGS = 15


class OllamaError(Exception):
    """Base error for Ollama integration failures."""


class OllamaConnectionError(OllamaError):
    """The Ollama server is not reachable."""


class OllamaModelNotFoundError(OllamaError):
    """The configured model is not installed in Ollama."""


class OllamaTimeoutError(OllamaError):
    """The request to Ollama timed out."""


class InvalidModelOutputError(OllamaError):
    """The model output could not be parsed into the expected schema."""


def check_health(base_url, model, timeout=HEALTH_TIMEOUT):
    """Check Ollama connectivity and whether the configured model is installed.

    Returns a tuple ``(reachable, model_available, detail)``.
    Never raises — a downgraded Ollama must not crash the app.
    """
    try:
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/tags", method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return False, False, f"Ollama responded with HTTP {exc.code}."
    except (urllib.error.URLError, socket.timeout, OSError, ValueError):
        return False, False, "Ollama is not reachable at the configured URL."

    names = [entry.get("name", "") for entry in data.get("models", [])]
    if model in names or any(name.startswith(model + ":") for name in names):
        return True, True, f"Ollama is reachable; model '{model}' is available."
    return True, False, (
        f"Ollama is reachable, but model '{model}' is not installed. "
        f"Pull it with: ollama pull {model}"
    )


def generate_content(base_url, model, prompt, timeout):
    """Generate structured product content via Ollama's /api/generate.

    Uses a non-streaming request with JSON output format. Retries once on
    malformed or schema-invalid output (bounded — never more than
    MAX_ATTEMPTS requests). Returns the validated content dict. Raises a
    specific OllamaError subclass on connectivity, model-availability,
    timeout, or invalid-output failures.
    """
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = _request_completion(base_url, model, prompt, timeout)
            return _validate_content(_parse_model_json(raw))
        except InvalidModelOutputError as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                continue
    raise last_error


def _request_completion(base_url, model, prompt, timeout):
    """Perform one non-streaming generation request and return raw text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.4, "num_predict": 1536},
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _read_http_error_body(exc)
        if exc.code == 404 or "not found" in detail.lower():
            raise OllamaModelNotFoundError(
                f"Model '{model}' is not installed. Pull it with: ollama pull {model}"
            ) from exc
        raise OllamaError(f"Ollama responded with HTTP {exc.code}: {detail}") from exc
    except socket.timeout as exc:
        raise OllamaTimeoutError("The request to Ollama timed out.") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise OllamaConnectionError(f"Cannot connect to Ollama: {exc}") from exc

    raw = body.get("response")
    if not isinstance(raw, str):
        raise InvalidModelOutputError("Ollama response did not contain generated text.")
    return raw


def _read_http_error_body(exc):
    try:
        data = json.loads(exc.read().decode("utf-8"))
        return str(data.get("error", ""))
    except Exception:
        return ""


def _parse_model_json(raw):
    """Parse the model's JSON, tolerating markdown code fences only."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except ValueError as exc:
        raise InvalidModelOutputError("Model output was not valid JSON.") from exc


def _validate_content(parsed):
    """Ensure the parsed model output matches the required schema exactly.

    Returns a normalised content dict. Hashtags are normalised to carry a
    leading '#' and to be unique. Raises InvalidModelOutputError on any
    violation so the caller can retry or fail cleanly.
    """
    if not isinstance(parsed, dict):
        raise InvalidModelOutputError("Model output must be a JSON object.")
    for field in REQUIRED_TEXT_FIELDS:
        value = parsed.get(field)
        if not isinstance(value, str) or not value.strip():
            raise InvalidModelOutputError(f"Field '{field}' is missing or empty.")

    captions = _validate_captions(parsed)
    hashtags = _normalise_hashtags(parsed.get("hashtags"))
    selling_points = _validate_selling_points(parsed.get("selling_points"))

    return {
        "product_title": parsed["product_title"].strip(),
        "instagram_captions": captions,
        "instagram_caption": captions[0],
        "whatsapp_message": parsed["whatsapp_message"].strip(),
        "product_description": parsed["product_description"].strip(),
        "selling_points": selling_points,
        "hashtags": hashtags,
        "cta_suggestion": parsed["cta_suggestion"].strip(),
        "marketplace_title": parsed["marketplace_title"].strip(),
    }


def _validate_captions(parsed):
    """Require exactly three distinct, non-empty Instagram captions."""
    captions = parsed.get("instagram_captions")
    if not isinstance(captions, list) or len(captions) != 3:
        raise InvalidModelOutputError(
            "'instagram_captions' must be an array of exactly three captions."
        )
    cleaned = []
    for index, caption in enumerate(captions, start=1):
        if not isinstance(caption, str) or not caption.strip():
            raise InvalidModelOutputError(
                f"Instagram caption {index} is missing or empty."
            )
        cleaned.append(caption.strip())
    if len(set(cleaned)) != len(cleaned):
        raise InvalidModelOutputError(
            "Instagram captions must be three distinct options, not duplicates."
        )
    return cleaned


def _normalise_hashtags(raw):
    """Normalise hashtags: leading '#', trimmed, unique, bounded in count."""
    if not isinstance(raw, list) or not raw:
        raise InvalidModelOutputError(
            "'hashtags' must be a non-empty array of strings."
        )
    seen = []
    for tag in raw:
        if not isinstance(tag, str) or not tag.strip():
            raise InvalidModelOutputError(
                "'hashtags' must be a non-empty array of strings."
            )
        tag = tag.strip()
        if not tag.startswith("#"):
            tag = "#" + tag.lstrip("#")
        if tag not in seen:
            seen.append(tag)
    if len(seen) > MAX_HASHTAGS:
        seen = seen[:MAX_HASHTAGS]
    return seen


def _validate_selling_points(raw):
    """Selling points are optional but must be a list of non-empty strings."""
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(
        isinstance(point, str) and point.strip() for point in raw
    ):
        raise InvalidModelOutputError(
            "'selling_points' must be an array of strings when provided."
        )
    return [point.strip() for point in raw]
