"""DukaanDraft Flask application (Phase 1).

A local-first AI sales content assistant. Inference goes only to the
configured local Ollama endpoint — there are no cloud fallbacks.
"""

import logging

from flask import Flask, jsonify, render_template, request

import config
from prompts.product_prompts import build_product_prompt
from services import ollama_service
from services.ollama_service import (
    InvalidModelOutputError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dukaandraft")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

OPTIONAL_FIELDS = ("category", "price", "features", "target_audience")


def _error_response(message, status_code, field_errors=None):
    body = {"success": False, "error": message}
    if field_errors:
        body["field_errors"] = field_errors
    return jsonify(body), status_code


def _validate_payload(payload):
    """Validate and clean the request payload.

    Returns ``(cleaned, field_errors)``. ``cleaned`` is only populated enough
    to build a prompt; when ``field_errors`` is non-empty the input is invalid.
    """
    errors = {}
    cleaned = {}

    product_name = payload.get("product_name")
    if product_name is None or (isinstance(product_name, str) and not product_name.strip()):
        errors["product_name"] = "Product name is required."
    elif not isinstance(product_name, str):
        errors["product_name"] = "Product name must be a string."
    elif len(product_name.strip()) > config.FIELD_LIMITS["product_name"]:
        errors["product_name"] = (
            f"Product name is too long "
            f"(max {config.FIELD_LIMITS['product_name']} characters)."
        )
    else:
        cleaned["product_name"] = product_name.strip()

    for field in OPTIONAL_FIELDS:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            cleaned[field] = None
            continue
        if not isinstance(value, str):
            errors[field] = f"{field.replace('_', ' ')} must be a string."
            continue
        value = value.strip()
        if len(value) > config.FIELD_LIMITS[field]:
            errors[field] = (
                f"{field.replace('_', ' ')} is too long "
                f"(max {config.FIELD_LIMITS[field]} characters)."
            )
            continue
        cleaned[field] = value

    language = payload.get("language")
    if language is None:
        errors["language"] = "Language is required."
    elif language not in config.SUPPORTED_LANGUAGES:
        errors["language"] = (
            "Language must be one of: " + ", ".join(config.SUPPORTED_LANGUAGES) + "."
        )
    else:
        cleaned["language"] = language

    return cleaned, errors


@app.get("/")
def index():
    return render_template(
        "index.html",
        languages=config.SUPPORTED_LANGUAGES,
        default_language="Hinglish",
        categories=config.PRODUCT_CATEGORIES,
    )


@app.get("/api/health")
def health():
    reachable, model_available, detail = ollama_service.check_health(
        config.OLLAMA_BASE_URL, config.OLLAMA_MODEL
    )
    healthy = reachable and model_available
    return jsonify(
        {
            "success": healthy,
            "status": "ok" if healthy else "degraded",
            "ollama": {
                "reachable": reachable,
                "model": config.OLLAMA_MODEL,
                "model_available": model_available,
                "detail": detail,
            },
        }
    )


@app.post("/api/generate")
def generate():
    payload = request.get_json(silent=True)
    if payload is None:
        return _error_response("Request body must be valid JSON.", 400)
    if not isinstance(payload, dict):
        return _error_response("Request body must be a JSON object.", 400)

    cleaned, field_errors = _validate_payload(payload)
    if field_errors:
        return _error_response("Invalid input. Please check the highlighted fields.", 422, field_errors)

    prompt = build_product_prompt(**cleaned)

    try:
        content = ollama_service.generate_content(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
            prompt=prompt,
            timeout=config.OLLAMA_TIMEOUT,
        )
    except OllamaConnectionError as exc:
        logger.warning("Ollama connection failed: %s", exc)
        return _error_response(
            "Cannot connect to Ollama. Make sure Ollama is running on this machine.", 503
        )
    except OllamaModelNotFoundError as exc:
        return _error_response(str(exc), 503)
    except OllamaTimeoutError:
        return _error_response(
            "The model took too long to respond. Please try again.", 504
        )
    except InvalidModelOutputError as exc:
        logger.warning("Invalid model output: %s", exc)
        return _error_response(
            "The model returned an invalid response. Please try again.", 502
        )
    except ollama_service.OllamaError as exc:
        logger.warning("Unexpected Ollama error: %s", exc)
        return _error_response(f"Ollama error: {exc}", 502)

    return jsonify({"success": True, "content": content, "model": config.OLLAMA_MODEL})


@app.errorhandler(413)
def request_too_large(_exc):
    return _error_response("Request body is too large.", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
