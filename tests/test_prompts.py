"""Tests for prompt construction."""

import unittest

from prompts.product_prompts import build_product_prompt


def build(**overrides):
    params = {
        "product_name": "Cotton Kurti",
        "category": "Clothing & Fashion",
        "price": "599",
        "features": "Breathable cotton fabric, blue colour",
        "target_audience": "College students",
        "language": "Hinglish",
    }
    params.update(overrides)
    return build_product_prompt(**params)


class PromptContentTest(unittest.TestCase):
    def test_includes_all_product_facts(self):
        prompt = build()
        self.assertIn("Cotton Kurti", prompt)
        self.assertIn("Clothing & Fashion", prompt)
        self.assertIn("₹599", prompt)
        self.assertIn("Breathable cotton fabric", prompt)
        self.assertIn("College students", prompt)

    def test_mentions_requested_language(self):
        self.assertIn("Hindi", build(language="Hindi"))
        self.assertIn("English", build(language="English"))
        self.assertIn("Hinglish", build(language="Hinglish"))

    def test_price_with_rupee_symbol_is_not_doubled(self):
        self.assertIn("₹599", build(price="₹599"))
        self.assertNotIn("₹₹", build(price="₹599"))


class PromptSchemaTest(unittest.TestCase):
    def test_requires_all_nine_json_keys(self):
        prompt = build()
        for key in (
            "product_title",
            "instagram_captions",
            "instagram_caption",
            "whatsapp_message",
            "product_description",
            "selling_points",
            "hashtags",
            "cta_suggestion",
            "marketplace_title",
        ):
            self.assertIn(key, prompt)

    def test_requires_three_distinct_caption_strategies(self):
        prompt = build()
        for phrase in ("Caption 1", "Caption 2", "Caption 3", "different approach"):
            self.assertIn(phrase, prompt)

    def test_hashtags_must_carry_hash_prefix(self):
        self.assertIn("# symbol", build())

    def test_emoji_discipline_rules_present(self):
        prompt = build()
        self.assertIn("emojis sparingly", prompt)


class PromptAccuracyTest(unittest.TestCase):
    def test_forbids_invented_claims(self):
        prompt = build()
        for phrase in (
            "Never invent discounts",
            "stock availability",
            "shipping or delivery commitments",
            "testimonials",
            "fake urgency",
        ):
            self.assertIn(phrase, prompt)

    def test_forbids_superlatives(self):
        self.assertIn('"best"', build())
        self.assertIn('"number one"', build())

    def test_requires_distinct_platform_content(self):
        prompt = build()
        self.assertIn("distinct from every caption", prompt)


class PromptCategoryTest(unittest.TestCase):
    def test_fashion_guidance_present_for_clothing(self):
        prompt = build(category="Clothing & Fashion")
        self.assertIn("style, versatility, outfit pairing", prompt)

    def test_electronics_guidance_present(self):
        prompt = build(category="Electronics")
        self.assertIn("specifications and practical uses", prompt)

    def test_beauty_guidance_restricts_claims(self):
        prompt = build(category="Beauty & Personal Care")
        self.assertIn("medical, safety or guaranteed-result claims", prompt)

    def test_home_guidance_present(self):
        prompt = build(category="Home & Living")
        self.assertIn("materials, design, use cases", prompt)

    def test_food_guidance_present(self):
        prompt = build(category="Food & Other")
        self.assertIn("ingredients, taste, packaging", prompt)

    def test_custom_category_gets_default_guidance(self):
        prompt = build(category="Pet Supplies")
        self.assertIn("CATEGORY: General", prompt)
        self.assertIn("factual copy", prompt)

    def test_no_category_gets_default_guidance(self):
        prompt = build(category=None)
        self.assertIn("General", prompt)


class PromptOptionalFieldsTest(unittest.TestCase):
    def test_missing_optional_fields_are_omitted(self):
        prompt = build(category=None, price=None, features=None, target_audience=None)
        self.assertNotIn("None", prompt)
        self.assertNotIn("Category:", prompt)
        self.assertNotIn("Price:", prompt)
        self.assertNotIn("Features:", prompt)
        self.assertNotIn("Target audience:", prompt)

    def test_blank_optional_fields_are_omitted(self):
        prompt = build(category="  ", price="", features="", target_audience="")
        self.assertNotIn("Category:", prompt)
        self.assertNotIn("Price:", prompt)

    def test_none_values_do_not_leak_into_prompt(self):
        prompt = build(price=None)
        self.assertNotIn("None", prompt)


if __name__ == "__main__":
    unittest.main()
