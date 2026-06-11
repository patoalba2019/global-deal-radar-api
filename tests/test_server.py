import importlib
import os
import unittest
from unittest.mock import patch


class GlobalDealRadarAPITest(unittest.TestCase):
    def setUp(self):
        os.environ["REQUIRE_PAID_GATEWAY"] = "false"
        os.environ["PAID_GATEWAY_SECRETS"] = "test-secret"
        os.environ["ENABLED_SOURCES"] = "cheapshark,slickdeals"
        self.server = importlib.import_module("server")
        self.server.cache["deals"] = []
        self.server.cache["metadata"] = {
            "api": self.server.APP_NAME,
            "version": self.server.APP_VERSION,
            "updated_at": None,
            "last_successful_refresh_at": None,
            "deal_count": 0,
            "sources": [],
            "source_errors": {},
        }
        self.client = self.server.app.test_client()

    def tearDown(self):
        for key in (
            "REQUIRE_PAID_GATEWAY",
            "PAID_GATEWAY_SECRETS",
            "PAID_GATEWAY_SECRET_HASHES",
            "ENABLED_SOURCES",
        ):
            os.environ.pop(key, None)

    def sample_deals(self):
        return [
            self.server.finalize_item(
                {
                    "id": "cheapshark-game",
                    "source": "cheapshark",
                    "source_item_id": "abc",
                    "item_type": "deal",
                    "title": "Great Game 80% off for $4.99",
                    "summary": "Source-provided game price.",
                    "deal_url": "https://example.com/game",
                    "source_url": "https://www.cheapshark.com/api/1.0/deals",
                    "published_at": "2026-06-05T12:00:00+00:00",
                    "merchant": "store",
                    "category": "gaming",
                    "price": 4.99,
                    "currency": "USD",
                    "normal_price": 24.99,
                    "discount_percent": 80,
                    "price_confidence": "source_provided",
                    "is_live_price": True,
                    "real_time_inventory": False,
                    "tags": ["gaming", "source-price"],
                }
            ),
            self.server.finalize_item(
                {
                    "id": "slickdeals-ai",
                    "source": "slickdeals",
                    "source_item_id": None,
                    "item_type": "deal",
                    "title": "AI writing software lifetime discount",
                    "summary": "Community deal post for AI software.",
                    "deal_url": "https://example.com/ai",
                    "source_url": "https://slickdeals.net/rss",
                    "published_at": "2026-06-05T10:00:00+00:00",
                    "merchant": "example.com",
                    "category": "ai-tools",
                    "price": None,
                    "currency": None,
                    "normal_price": None,
                    "discount_percent": None,
                    "price_confidence": "not_detected",
                    "is_live_price": False,
                    "real_time_inventory": False,
                    "tags": ["ai-tools", "software"],
                }
            ),
        ]

    def test_health_is_public(self):
        os.environ["REQUIRE_PAID_GATEWAY"] = "true"
        with patch.object(
            self.server,
            "snapshot",
            return_value={
                "deals": [],
                "metadata": {
                    "api": self.server.APP_NAME,
                    "version": self.server.APP_VERSION,
                    "updated_at": "2026-06-11T00:00:00+00:00",
                    "last_successful_refresh_at": "2026-06-11T00:00:00+00:00",
                    "deal_count": 2,
                    "sources": ["cheapshark", "slickdeals"],
                    "source_errors": {},
                },
            },
        ):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["api"], "GlobalDealRadarAPI")
        self.assertTrue(data["catalog_ready"])
        self.assertEqual(data["deal_signal_count"], 2)
        self.assertEqual(data["active_source_count"], 2)
        self.assertNotIn("cache", data)

    def test_paid_gateway_blocks_data_and_accepts_secret(self):
        os.environ["REQUIRE_PAID_GATEWAY"] = "true"
        os.environ["PAID_GATEWAY_SECRETS"] = "rapidapi-secret"
        with patch.object(self.server, "snapshot", return_value={"deals": self.sample_deals(), "metadata": {}}):
            self.assertEqual(self.client.get("/deals").status_code, 402)
            allowed = self.client.get(
                "/deals",
                headers={"X-RapidAPI-Proxy-Secret": "rapidapi-secret"},
            )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.get_json()["metadata"]["matched"], 2)

    def test_filters_categories_and_search(self):
        with patch.object(self.server, "snapshot", return_value={"deals": self.sample_deals(), "metadata": {}}):
            response = self.client.get("/deals?category=ai-tools&q=writing")
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["metadata"]["matched"], 1)
        self.assertEqual(data["deals"][0]["id"], "slickdeals-ai")

    def test_stats_counts_priced_source_items(self):
        with patch.object(self.server, "snapshot", return_value={"deals": self.sample_deals(), "metadata": {}}):
            response = self.client.get("/stats")
        stats = response.get_json()["stats"]
        self.assertEqual(stats["total_items"], 2)
        self.assertEqual(stats["by_category"]["gaming"], 1)
        self.assertEqual(stats["priced_items"], 1)
        self.assertEqual(stats["source_price_items"], 1)

    def test_price_and_category_detection_include_audiobooks_and_recipes(self):
        price = self.server.parse_price_signal("Audible cookbook bundle 75% off for $9.99")
        self.assertEqual(price["currency"], "USD")
        self.assertEqual(price["price"], 9.99)
        self.assertEqual(price["discount_percent"], 75)
        self.assertEqual(
            self.server.detect_category("Audible audiobook bundle Kindle novel subscription"),
            "books-audiobooks",
        )
        self.assertEqual(
            self.server.detect_category("1000 savory dinner recipes kitchen cooking"),
            "food-recipes",
        )

    def test_parser_avoids_false_discount_and_category_matches(self):
        cotton = self.server.parse_price_signal("9-pk Men's Classic 100% Cotton Undershirts $20.70")
        self.assertEqual(cotton["price"], 20.70)
        self.assertIsNone(cotton["discount_percent"])
        self.assertNotEqual(self.server.detect_category("Woot daily deals and vacuums"), "ai-tools")
        self.assertNotEqual(self.server.detect_category("Men's Classic undershirts"), "courses")

    def test_search_links_can_focus_audiobooks(self):
        response = self.client.get("/search-links?q=spanish%20audiobook&category=books-audiobooks")
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["links"][0]["provider"], "Audible")


if __name__ == "__main__":
    unittest.main()
