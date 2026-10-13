"""Endpoint tests for the DukaanDraft Flask app.

All Ollama calls are mocked — these tests require no running model and no
internet access.
"""

import json
import unittest
from unittest.mock import patch

import config
from app import app

VALID_CONTENT = {
    "product_title": "Indigo Cotton Kurti — Everyday Comfort",
    "instagram_captions": [
        "Breathable cotton kurti in indigo blue.",
        "College days call for easy comfort.",
        "Simple. Soft. Yours.",
    ],
    "instagram_caption": "Breathable cotton kurti in indigo blue.",
    "whatsapp_message": "New cotton kurti just arrived!",
    "product_description": "A breathable cotton kurti in indigo blue, made for daily wear.",
    "selling_points": ["Breathable cotton fabric", "Indigo blue colour"],
    "hashtags": ["#CottonKurti", "#EthnicWear"],
    "cta_suggestion": "Send us a message to order yours today.",
    "marketplace_title": "Indigo Blue Cotton Kurti for Women — Daily Wear",
}


class BaseAppTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()


class LandingPageTest(BaseAppTest):
    def test_landing_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("DukaanDraft", body)

    def test_landing_page_has_premium_studio_content(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for phrase in (
            "Turn product details into content that sells.",
            "Create product content",
            "Try a sample product",
        ):
            self.assertIn(phrase, body)

    def test_landing_page_has_workspace_controls(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for phrase in (
            "Product workspace",
            "category_custom",
            "Custom category",
            "sample-chip",
            "Content language",
        ):
            self.assertIn(phrase, body)

    def test_landing_page_offers_all_supported_languages(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for language in config.SUPPORTED_LANGUAGES:
            self.assertIn(language, body)

    def test_landing_page_offers_all_product_categories(self):
        from html import escape

        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for category in config.PRODUCT_CATEGORIES:
            self.assertIn(escape(category), body)

    def test_landing_page_has_all_results_sections(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)
        for section_id in (
            "product_title",
            "marketplace_title",
            "caption_option_1",
            "caption_option_2",
            "caption_option_3",
            "whatsapp_message",
            "product_description",
            "selling_points",
            "hashtags",
            "cta_suggestion",
            "copy-all",
        ):
            self.assertIn(section_id, body)


class HealthEndpointTest(BaseAppTest):
    @patch("services.ollama_service.check_health")
    def test_health_ok_when_ollama_and_model_available(self, mock_check):
        mock_check.return_value = (True, True, "all good")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["ollama"]["reachable"])
        self.assertTrue(data["ollama"]["model_available"])
        self.assertEqual(data["ollama"]["model"], config.OLLAMA_MODEL)

    @patch("services.ollama_service.check_health")
    def test_health_reports_degraded_when_ollama_unavailable(self, mock_check):
        mock_check.return_value = (False, False, "Ollama is not reachable at the configured URL.")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["ollama"]["reachable"])
        self.assertFalse(data["ollama"]["model_available"])

    @patch("services.ollama_service.check_health")
    def test_health_reports_model_missing_when_ollama_up(self, mock_check):
        mock_check.return_value = (True, False, "model not installed")
        response = self.client.get("/api/health")
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data["ollama"]["reachable"])
        self.assertFalse(data["ollama"]["model_available"])


class GenerateValidationTest(BaseAppTest):
    def test_malformed_json_is_rejected(self):
        response = self.client.post(
            "/api/generate", data="{not valid json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        self.assertIn("valid JSON", response.get_json()["error"])

    def test_non_object_json_is_rejected(self):
        response = self.client.post(
            "/api/generate", data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_missing_product_name_is_rejected(self):
        response = self.client.post("/api/generate", json={"language": "English"})
        self.assertEqual(response.status_code, 422)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertIn("product_name", data["field_errors"])

    def test_blank_product_name_is_rejected(self):
        response = self.client.post(
            "/api/generate", json={"product_name": "   ", "language": "English"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("product_name", response.get_json()["field_errors"])

    def test_invalid_language_is_rejected(self):
        response = self.client.post(
            "/api/generate", json={"product_name": "Kurti", "language": "French"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("language", response.get_json()["field_errors"])

    def test_wrong_field_type_is_rejected(self):
        response = self.client.post(
            "/api/generate",
            json={"product_name": "Kurti", "price": 599, "language": "English"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("price", response.get_json()["field_errors"])

    def test_overly_long_input_is_rejected(self):
        response = self.client.post(
            "/api/generate",
            json={"product_name": "x" * 200, "language": "English"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("product_name", response.get_json()["field_errors"])

    def test_empty_body_is_rejected(self):
        response = self.client.post("/api/generate", json={})
        self.assertEqual(response.status_code, 422)


class GenerateSuccessTest(BaseAppTest):
    @patch("services.ollama_service.generate_content")
    def test_valid_input_reaches_generation_service(self, mock_generate):
        mock_generate.return_value = VALID_CONTENT
        payload = {
            "product_name": "Cotton Kurti",
            "category": "Clothing & Fashion",
            "price": "599",
            "features": "Breathable cotton fabric, blue colour",
            "target_audience": "College students",
            "language": "Hinglish",
        }
        response = self.client.post("/api/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_generate.assert_called_once()
        _, kwargs = mock_generate.call_args
        self.assertEqual(kwargs["model"], config.OLLAMA_MODEL)
        self.assertIn("Cotton Kurti", kwargs["prompt"])

        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["model"], config.OLLAMA_MODEL)
        for key in VALID_CONTENT:
            self.assertEqual(data["content"][key], VALID_CONTENT[key])

    @patch("services.ollama_service.generate_content")
    def test_backward_compatible_primary_caption(self, mock_generate):
        mock_generate.return_value = VALID_CONTENT
        response = self.client.post(
            "/api/generate",
            json={"product_name": "Kurti", "language": "English"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(
            data["content"]["instagram_caption"],
            data["content"]["instagram_captions"][0],
        )

    @patch("services.ollama_service.generate_content")
    def test_optional_fields_may_be_omitted(self, mock_generate):
        mock_generate.return_value = VALID_CONTENT
        response = self.client.post(
            "/api/generate", json={"product_name": "Kurti", "language": "English"}
        )
        self.assertEqual(response.status_code, 200)
        _, kwargs = mock_generate.call_args
        self.assertEqual(kwargs["model"], config.OLLAMA_MODEL)
        self.assertIn("Kurti", kwargs["prompt"])
        self.assertNotIn("None", kwargs["prompt"])


class GenerateOllamaFailureTest(BaseAppTest):
    def _post(self):
        return self.client.post(
            "/api/generate", json={"product_name": "Kurti", "language": "English"}
        )

    @patch("services.ollama_service.generate_content")
    def test_connection_error_returns_503(self, mock_generate):
        from services.ollama_service import OllamaConnectionError

        mock_generate.side_effect = OllamaConnectionError("refused")
        response = self._post()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["success"])

    @patch("services.ollama_service.generate_content")
    def test_model_not_found_returns_503_with_pull_hint(self, mock_generate):
        from services.ollama_service import OllamaModelNotFoundError

        mock_generate.side_effect = OllamaModelNotFoundError(
            "Model 'gemma3:4b' is not installed. Pull it with: ollama pull gemma3:4b"
        )
        response = self._post()
        self.assertEqual(response.status_code, 503)
        self.assertIn("ollama pull", response.get_json()["error"])

    @patch("services.ollama_service.generate_content")
    def test_timeout_returns_504(self, mock_generate):
        from services.ollama_service import OllamaTimeoutError

        mock_generate.side_effect = OllamaTimeoutError("too slow")
        response = self._post()
        self.assertEqual(response.status_code, 504)
        self.assertFalse(response.get_json()["success"])

    @patch("services.ollama_service.generate_content")
    def test_invalid_model_output_returns_502(self, mock_generate):
        from services.ollama_service import InvalidModelOutputError

        mock_generate.side_effect = InvalidModelOutputError("bad json")
        response = self._post()
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
