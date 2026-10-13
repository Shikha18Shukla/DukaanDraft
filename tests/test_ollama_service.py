"""Tests for the Ollama service layer.

urllib.request.urlopen is mocked, so these tests need no running Ollama
server and no internet access.
"""

import io
import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from services import ollama_service
from services.ollama_service import (
    InvalidModelOutputError,
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)

VALID_PAYLOAD = {
    "product_title": "Indigo Cotton Kurti — Everyday Comfort",
    "instagram_captions": [
        "Breathable cotton kurti in indigo blue.",
        "College days call for easy comfort.",
        "Simple. Soft. Yours.",
    ],
    "instagram_caption": "Breathable cotton kurti in indigo blue.",
    "whatsapp_message": "New cotton kurti just arrived!",
    "product_description": "A breathable cotton kurti in indigo blue, made for daily wear.",
    "selling_points": ["Breathable cotton fabric", "Indigo blue colour", "Machine washable"],
    "hashtags": ["#CottonKurti", "#EthnicWear", "#CollegeFashion"],
    "cta_suggestion": "Send us a message to order yours today.",
    "marketplace_title": "Indigo Blue Cotton Kurti for Women — Daily Wear",
}


class _FakeResponse:
    """Minimal context-manager response matching urllib's interface."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(code, message):
    body = json.dumps({"error": message}).encode("utf-8")
    fp = io.BytesIO(body)
    return urllib.error.HTTPError(
        "http://127.0.0.1:11434/api/generate", code, "err", {}, fp
    )


def _valid_response():
    return _FakeResponse({"response": json.dumps(VALID_PAYLOAD)})


class GenerateContentTest(unittest.TestCase):
    def _generate(self, responses):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            if isinstance(responses, list):
                mock_urlopen.side_effect = responses
            else:
                mock_urlopen.return_value = responses
            return ollama_service.generate_content(
                "http://127.0.0.1:11434", "gemma3:4b", "test prompt", 30
            )

    def _respond(self, payload):
        return _FakeResponse({"response": json.dumps(payload)})

    def test_valid_model_json_is_parsed_and_returned(self):
        content = self._generate(_valid_response())
        self.assertEqual(content["product_title"], VALID_PAYLOAD["product_title"])
        self.assertEqual(content["instagram_captions"], VALID_PAYLOAD["instagram_captions"])
        self.assertEqual(content["selling_points"], VALID_PAYLOAD["selling_points"])

    def test_backward_compatible_primary_caption_matches_first_option(self):
        content = self._generate(_valid_response())
        self.assertEqual(
            content["instagram_caption"], content["instagram_captions"][0]
        )

    def test_json_wrapped_in_code_fences_is_tolerated(self):
        fenced = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse({"response": fenced})
            content = ollama_service.generate_content(
                "http://127.0.0.1:11434", "gemma3:4b", "p", 30
            )
        self.assertEqual(content["product_title"], VALID_PAYLOAD["product_title"])

    def test_non_streaming_json_format_is_requested(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _valid_response()
            ollama_service.generate_content("http://127.0.0.1:11434", "gemma3:4b", "p", 30)
        request = mock_urlopen.call_args[0][0]
        sent = json.loads(request.data.decode("utf-8"))
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["format"], "json")
        self.assertEqual(sent["model"], "gemma3:4b")

    def test_single_request_on_success(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _valid_response()
            ollama_service.generate_content("http://127.0.0.1:11434", "gemma3:4b", "p", 30)
        self.assertEqual(mock_urlopen.call_count, 1)

    # --- caption validation -------------------------------------------------

    def test_two_captions_are_rejected(self):
        broken = dict(VALID_PAYLOAD, instagram_captions=["one", "two"])
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    def test_duplicate_captions_are_rejected(self):
        broken = dict(
            VALID_PAYLOAD,
            instagram_captions=["same text", "same text", "same text"],
        )
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    def test_empty_caption_is_rejected(self):
        broken = dict(VALID_PAYLOAD, instagram_captions=["one", "  ", "three"])
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    # --- other new-field validation -----------------------------------------

    def test_missing_selling_points_defaults_to_empty_list(self):
        payload = dict(VALID_PAYLOAD)
        del payload["selling_points"]
        content = self._generate(self._respond(payload))
        self.assertEqual(content["selling_points"], [])

    def test_malformed_selling_points_are_rejected(self):
        broken = dict(VALID_PAYLOAD, selling_points="breathable cotton")
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    def test_missing_cta_or_marketplace_title_is_rejected(self):
        for field in ("cta_suggestion", "marketplace_title"):
            broken = dict(VALID_PAYLOAD)
            del broken[field]
            with self.assertRaises(InvalidModelOutputError):
                self._generate(self._respond(broken))

    # --- hashtag normalisation ----------------------------------------------

    def test_hashtags_without_hash_prefix_are_normalised(self):
        payload = dict(VALID_PAYLOAD, hashtags=["CottonKurti", "#EthnicWear"])
        content = self._generate(self._respond(payload))
        self.assertEqual(content["hashtags"], ["#CottonKurti", "#EthnicWear"])

    def test_duplicate_hashtags_are_removed(self):
        payload = dict(VALID_PAYLOAD, hashtags=["#CottonKurti", "#CottonKurti", "#ethnicwear"])
        content = self._generate(self._respond(payload))
        self.assertEqual(content["hashtags"], ["#CottonKurti", "#ethnicwear"])

    # --- generic output failures --------------------------------------------

    def test_malformed_model_json_is_rejected(self):
        with self.assertRaises(InvalidModelOutputError):
            self._generate(_FakeResponse({"response": "this is not json"}))

    def test_incomplete_model_output_is_rejected(self):
        broken = dict(VALID_PAYLOAD)
        del broken["hashtags"]
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    def test_empty_text_field_is_rejected(self):
        broken = dict(VALID_PAYLOAD, product_title="  ")
        with self.assertRaises(InvalidModelOutputError):
            self._generate(self._respond(broken))

    def test_non_object_model_output_is_rejected(self):
        with self.assertRaises(InvalidModelOutputError):
            self._generate(_FakeResponse({"response": json.dumps(["a", "b"])}))


class GenerateContentRetryTest(unittest.TestCase):
    def test_one_retry_then_success(self):
        bad = _FakeResponse({"response": "not json"})
        good = _valid_response()
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [bad, good]
            content = ollama_service.generate_content(
                "http://127.0.0.1:11434", "gemma3:4b", "p", 30
            )
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(content["product_title"], VALID_PAYLOAD["product_title"])

    def test_two_failures_raise_invalid_output(self):
        bad = _FakeResponse({"response": "not json"})
        with self.assertRaises(InvalidModelOutputError):
            with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = [bad, bad]
                ollama_service.generate_content(
                    "http://127.0.0.1:11434", "gemma3:4b", "p", 30
                )

    def test_no_retry_on_connection_error(self):
        with self.assertRaises(OllamaConnectionError):
            with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = urllib.error.URLError("refused")
                ollama_service.generate_content(
                    "http://127.0.0.1:11434", "gemma3:4b", "p", 30
                )


class GenerateContentErrorTest(unittest.TestCase):
    def _generate_with_error(self, error):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = error
            ollama_service.generate_content(
                "http://127.0.0.1:11434", "gemma3:4b", "p", 30
            )

    def test_connection_error_is_classified(self):
        with self.assertRaises(OllamaConnectionError):
            self._generate_with_error(urllib.error.URLError("connection refused"))

    def test_timeout_is_classified(self):
        with self.assertRaises(OllamaTimeoutError):
            self._generate_with_error(socket.timeout("timed out"))

    def test_http_404_means_model_not_found(self):
        with self.assertRaises(OllamaModelNotFoundError):
            self._generate_with_error(_http_error(404, "model not found"))

    def test_other_http_errors_are_generic_ollama_errors(self):
        with self.assertRaises(OllamaError) as ctx:
            self._generate_with_error(_http_error(500, "internal explosion"))
        self.assertNotIsInstance(ctx.exception, OllamaModelNotFoundError)


class CheckHealthTest(unittest.TestCase):
    def test_reachable_with_model_installed(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(
                {"models": [{"name": "gemma3:4b"}]}
            )
            reachable, available, detail = ollama_service.check_health(
                "http://127.0.0.1:11434", "gemma3:4b"
            )
        self.assertTrue(reachable)
        self.assertTrue(available)
        self.assertIn("gemma3:4b", detail)

    def test_reachable_with_tagged_model_name(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(
                {"models": [{"name": "gemma3:4b:latest"}]}
            )
            _, available, _ = ollama_service.check_health(
                "http://127.0.0.1:11434", "gemma3:4b"
            )
        self.assertTrue(available)

    def test_reachable_but_model_missing(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _FakeResponse(
                {"models": [{"name": "llama3.2"}]}
            )
            reachable, available, detail = ollama_service.check_health(
                "http://127.0.0.1:11434", "gemma3:4b"
            )
        self.assertTrue(reachable)
        self.assertFalse(available)

    def test_unreachable_ollama_is_reported_without_raising(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("refused")
            reachable, available, detail = ollama_service.check_health(
                "http://127.0.0.1:11434", "gemma3:4b"
            )
        self.assertFalse(reachable)
        self.assertFalse(available)
        self.assertIn("not reachable", detail)

    def test_http_error_is_reported_without_raising(self):
        with patch("services.ollama_service.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = _http_error(503, "unavailable")
            reachable, available, _ = ollama_service.check_health(
                "http://127.0.0.1:11434", "gemma3:4b"
            )
        self.assertFalse(reachable)
        self.assertFalse(available)


if __name__ == "__main__":
    unittest.main()
