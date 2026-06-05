from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree

import requests
from flask import Flask, jsonify, request


APP_NAME = "GlobalDealRadarAPI"
APP_VERSION = "1.0.0"
DEFAULT_PAID_GATEWAY_SECRET_HASHES = (
    "fb4d84f55fe8c752d0daf9bd9b381f07bbd9b3e05c9a513a3752764894bdcae0"
)
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("SOURCE_TIMEOUT_SECONDS", "15"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "1800"))
DEFAULT_LIMIT = int(os.environ.get("DEFAULT_LIMIT", "25"))
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", "100"))
USER_AGENT = os.environ.get(
    "SOURCE_USER_AGENT",
    "GlobalDealRadarAPI/1.0 (+https://rapidapi.com/patoalba2019/api/globaldealradarapi)",
)
ENABLED_SOURCES = {
    source.strip().lower()
    for source in os.environ.get(
        "ENABLED_SOURCES",
        "cheapshark,slickdeals,dealnews,techbargains,reddit_deals,hn_algolia,github_resources",
    ).split(",")
    if source.strip()
}

SOURCE_METADATA = {
    "cheapshark": {
        "name": "CheapShark",
        "website": "https://www.cheapshark.com",
        "source_url": "https://www.cheapshark.com/api/1.0/deals",
        "item_type": "deal",
        "strength": "Game deals with source-provided sale price, normal price, savings and redirect URL.",
    },
    "slickdeals": {
        "name": "Slickdeals Frontpage RSS",
        "website": "https://slickdeals.net",
        "source_url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
        "item_type": "deal",
        "strength": "Frontpage community deal posts across shopping, electronics, travel and services.",
    },
    "dealnews": {
        "name": "DealNews RSS",
        "website": "https://www.dealnews.com",
        "source_url": "https://www.dealnews.com/?rss=1",
        "item_type": "deal",
        "strength": "Editorial daily deal posts across consumer categories.",
    },
    "techbargains": {
        "name": "TechBargains RSS",
        "website": "https://www.techbargains.com",
        "source_url": "https://www.techbargains.com/rss.xml",
        "item_type": "deal",
        "strength": "Technology and electronics bargain feed.",
    },
    "reddit_deals": {
        "name": "Reddit r/deals RSS",
        "website": "https://www.reddit.com/r/deals/",
        "source_url": "https://www.reddit.com/r/deals/.rss",
        "item_type": "deal",
        "strength": "Community deal discussions with original outbound links where available.",
    },
    "hn_algolia": {
        "name": "Hacker News Algolia",
        "website": "https://hn.algolia.com",
        "source_url": "https://hn.algolia.com/api",
        "item_type": "market_signal",
        "strength": "Fresh software, startup, AI, hosting and pricing-related market signals.",
    },
    "github_resources": {
        "name": "GitHub Search",
        "website": "https://github.com",
        "source_url": "https://api.github.com/search/repositories",
        "item_type": "resource_list",
        "strength": "Popular curated lists for seasonal deals and discount resources.",
    },
}

RSS_SOURCE_NAMES = {"slickdeals", "dealnews", "techbargains", "reddit_deals"}

CATEGORY_DEFINITIONS = {
    "shopping": "Retail and general consumer discounts.",
    "electronics": "Computers, phones, appliances and tech hardware.",
    "software": "SaaS, desktop apps, developer tools and productivity software.",
    "ai-tools": "AI services, model platforms, agents and automation tools.",
    "courses": "Online courses, bootcamps, training and certifications.",
    "gaming": "Video games and gaming services.",
    "travel": "Flights, hotels, tourism, luggage and travel packages.",
    "hosting-domains": "Hosting, domains, cloud credits, VPNs and infrastructure.",
    "books-audiobooks": "Books, audiobooks, Kindle, Audible and reading subscriptions.",
    "food-recipes": "Food, recipes, cookbooks, groceries and kitchen content.",
    "finance": "Banking, cards, trading tools and money-related offers.",
    "digital-products": "Templates, assets, downloads, memberships and digital goods.",
    "business": "Business operations, marketing, sales and entrepreneur tools.",
    "general": "Useful deal or opportunity that does not fit a narrower category.",
}

CATEGORY_KEYWORDS = {
    "ai-tools": (
        "ai",
        "artificial intelligence",
        "chatgpt",
        "openai",
        "llm",
        "agent",
        "automation",
        "prompt",
        "midjourney",
        "claude",
    ),
    "software": (
        "software",
        "app",
        "saas",
        "subscription",
        "license",
        "productivity",
        "developer",
        "windows",
        "mac",
        "vpn",
        "notion",
        "office",
    ),
    "hosting-domains": (
        "hosting",
        "domain",
        "cloud",
        "server",
        "vps",
        "aws",
        "azure",
        "google cloud",
        "dns",
        "wordpress",
    ),
    "courses": (
        "course",
        "courses",
        "class",
        "bootcamp",
        "training",
        "certification",
        "udemy",
        "coursera",
        "skillshare",
        "masterclass",
    ),
    "gaming": (
        "game",
        "gaming",
        "steam",
        "xbox",
        "playstation",
        "nintendo",
        "switch",
        "epic games",
    ),
    "travel": (
        "flight",
        "hotel",
        "travel",
        "tour",
        "vacation",
        "airline",
        "cruise",
        "resort",
        "booking",
        "luggage",
        "package",
    ),
    "electronics": (
        "laptop",
        "monitor",
        "tv",
        "phone",
        "iphone",
        "android",
        "tablet",
        "camera",
        "headphones",
        "ssd",
        "router",
        "printer",
    ),
    "books-audiobooks": (
        "book",
        "ebook",
        "kindle",
        "audible",
        "audiobook",
        "audiobooks",
        "novel",
        "reading",
    ),
    "food-recipes": (
        "recipe",
        "recipes",
        "cookbook",
        "cooking",
        "kitchen",
        "baking",
        "dessert",
        "sweet",
        "savory",
        "food",
        "meal",
        "grocery",
    ),
    "finance": (
        "bank",
        "card",
        "cashback",
        "crypto",
        "trading",
        "broker",
        "finance",
        "loan",
        "invest",
    ),
    "digital-products": (
        "template",
        "theme",
        "plugin",
        "download",
        "asset",
        "bundle",
        "font",
        "icon",
        "stock",
    ),
    "business": (
        "crm",
        "sales",
        "marketing",
        "lead",
        "invoice",
        "startup",
        "business",
        "ecommerce",
        "shopify",
    ),
    "shopping": (
        "deal",
        "coupon",
        "discount",
        "sale",
        "clearance",
        "offer",
        "promo",
        "rebate",
        "warehouse",
    ),
}

PRICE_PATTERN = re.compile(
    r"(?P<symbol>[$€£])\s?(?P<amount>\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)"
    r"|(?P<amount2>\d{1,6}(?:[.,]\d{1,2})?)\s?(?P<code>USD|EUR|GBP|CAD|AUD)",
    re.IGNORECASE,
)
DISCOUNT_PATTERN = re.compile(r"(?<!\d)(?P<percent>\d{1,3})\s?%", re.IGNORECASE)
DISCOUNT_CONTEXT_PATTERN = re.compile(
    r"\b(off|save|savings|discount|coupon|promo|sale|markdown|rebate|cashback)\b",
    re.IGNORECASE,
)


app = Flask(__name__)
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
PUBLIC_PATHS = {"/health", "/openapi.json"}


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS
    response.headers[
        "Access-Control-Allow-Headers"
    ] = "Authorization, Content-Type, X-RapidAPI-Proxy-Secret, X-API-Gateway-Secret"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.before_request
def enforce_paid_gateway():
    if request.method == "OPTIONS" or request.path in PUBLIC_PATHS:
        return None
    if os.environ.get("REQUIRE_PAID_GATEWAY", "true").lower() not in {"1", "true", "yes"}:
        return None

    configured = os.environ.get("PAID_GATEWAY_SECRETS") or os.environ.get("PAID_GATEWAY_SECRET")
    expected = [secret.strip() for secret in (configured or "").split(",") if secret.strip()]
    configured_hashes = os.environ.get(
        "PAID_GATEWAY_SECRET_HASHES", DEFAULT_PAID_GATEWAY_SECRET_HASHES
    )
    expected_hashes = [value.strip().lower() for value in configured_hashes.split(",") if value.strip()]
    if not expected and not expected_hashes:
        return jsonify({"error": "Paid gateway is required but not configured."}), 503

    provided = (
        request.headers.get("X-RapidAPI-Proxy-Secret")
        or request.headers.get("X-API-Gateway-Secret")
        or request.headers.get("X-GlobalDealRadarAPI-Secret")
        or ""
    )
    provided_hash = hashlib.sha256(provided.encode("utf-8")).hexdigest()
    plaintext_match = any(hmac.compare_digest(provided, secret) for secret in expected)
    hash_match = any(hmac.compare_digest(provided_hash, value) for value in expected_hashes)
    if not plaintext_match and not hash_match:
        return (
            jsonify(
                {
                    "error": "Access denied. Subscribe through the authorized API marketplace to use this API.",
                    "marketplace": "RapidAPI",
                }
            ),
            402,
        )
    return None


cache_lock = threading.RLock()
refresh_lock = threading.Lock()
cache = {
    "deals": [],
    "metadata": {
        "api": APP_NAME,
        "version": APP_VERSION,
        "updated_at": None,
        "last_successful_refresh_at": None,
        "deal_count": 0,
        "sources": [],
        "source_errors": {},
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: object, max_length: int = 500) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length].strip()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.lower()


def parse_datetime(value: object) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    for suffix in ("Z", "+00:00"):
        candidate = text[:-1] + "+00:00" if suffix == "Z" and text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            continue
    return None


def stable_id(source: str, title: str, url: str) -> str:
    digest = hashlib.sha1(f"{source}:{title}:{url}".encode("utf-8")).hexdigest()[:16]
    return f"{source}-{digest}"


def domain_from_url(url: str) -> str | None:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return None
    return host[4:] if host.startswith("www.") else host or None


def parse_price_signal(text: str) -> dict:
    cleaned = clean_text(text, 1000)
    price_match = PRICE_PATTERN.search(cleaned)
    discount_match = DISCOUNT_PATTERN.search(cleaned)
    currency = None
    price = None
    if price_match:
        symbol = price_match.group("symbol")
        code = price_match.group("code")
        amount = price_match.group("amount") or price_match.group("amount2")
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(symbol, (code or "").upper())
        try:
            price = float(amount.replace(",", ""))
        except (AttributeError, ValueError):
            price = None
    discount_percent = None
    if discount_match:
        try:
            value = int(discount_match.group("percent"))
            start = max(0, discount_match.start() - 24)
            end = min(len(cleaned), discount_match.end() + 24)
            context = cleaned[start:end]
            if 0 < value <= 100 and DISCOUNT_CONTEXT_PATTERN.search(context):
                discount_percent = value
        except ValueError:
            discount_percent = None
    return {
        "currency": currency,
        "price": price,
        "discount_percent": discount_percent,
        "price_confidence": "text_extracted" if price is not None else "not_detected",
    }


def keyword_matches(text: str, keyword: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    if " " in normalized_keyword:
        return normalized_keyword in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", text) is not None


def detect_category(*parts: object) -> str:
    text = normalize_text(" ".join(clean_text(part, 1000) for part in parts))
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for keyword in keywords if keyword_matches(text, keyword))
    best_category = max(scores, key=scores.get)
    return best_category if scores[best_category] > 0 else "general"


def build_tags(title: str, category: str, source: str) -> list[str]:
    text = normalize_text(title)
    tags = {category, source.replace("_", "-")}
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if category_name == category:
            continue
        if any(keyword_matches(text, keyword) for keyword in keywords[:6]):
            tags.add(category_name)
    return sorted(tags)


def deal_score(item: dict) -> int:
    score = 45
    discount = item.get("discount_percent")
    if isinstance(discount, (int, float)):
        score += min(35, int(float(discount) * 0.45))
    if item.get("price") is not None:
        score += 5
    if item.get("normal_price") and item.get("price"):
        score += 5
    if item.get("category") in {"ai-tools", "software", "travel", "hosting-domains", "courses"}:
        score += 6
    if item.get("item_type") == "deal":
        score += 6
    elif item.get("item_type") == "market_signal":
        score += 2
    published_at = parse_datetime(item.get("published_at"))
    if published_at:
        try:
            published = datetime.fromisoformat(published_at)
            age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
            if age_hours <= 24:
                score += 8
            elif age_hours <= 72:
                score += 4
        except ValueError:
            pass
    return max(1, min(100, int(score)))


def http_get(url: str, params: dict | None = None) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/xml,*/*"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def finalize_item(item: dict) -> dict:
    item.setdefault("fetched_at", now_iso())
    item.setdefault("category", detect_category(item.get("title"), item.get("summary")))
    item.setdefault("tags", build_tags(item.get("title", ""), item["category"], item["source"]))
    item.setdefault("merchant", domain_from_url(item.get("deal_url", "")) or item["source"])
    item.setdefault("price", None)
    item.setdefault("currency", None)
    item.setdefault("normal_price", None)
    item.setdefault("discount_percent", None)
    item.setdefault("image_url", None)
    item.setdefault("is_live_price", False)
    item.setdefault("real_time_inventory", False)
    item.setdefault("score", deal_score(item))
    item.setdefault("source_attribution", SOURCE_METADATA[item["source"]]["name"])
    return item


def fetch_cheapshark(limit: int = 60) -> list[dict]:
    response = http_get(
        SOURCE_METADATA["cheapshark"]["source_url"],
        params={"pageSize": str(min(limit, 60)), "sortBy": "Deal Rating", "desc": "1", "onSale": "1"},
    )
    deals = []
    for raw in response.json():
        title = clean_text(raw.get("title"))
        deal_id = clean_text(raw.get("dealID"))
        sale_price = float(raw.get("salePrice") or 0)
        normal_price = float(raw.get("normalPrice") or 0)
        savings = float(raw.get("savings") or 0)
        item = {
            "id": stable_id("cheapshark", title, deal_id),
            "source": "cheapshark",
            "source_item_id": deal_id,
            "item_type": "deal",
            "title": title,
            "summary": "Game deal with source-provided sale price, normal price and savings.",
            "deal_url": f"https://www.cheapshark.com/redirect?dealID={quote_plus(deal_id)}",
            "source_url": SOURCE_METADATA["cheapshark"]["source_url"],
            "published_at": None,
            "merchant": f"CheapShark store {raw.get('storeID')}",
            "category": "gaming",
            "price": sale_price,
            "currency": "USD",
            "normal_price": normal_price,
            "discount_percent": round(savings, 2) if savings else None,
            "price_confidence": "source_provided",
            "is_live_price": True,
            "real_time_inventory": False,
            "image_url": raw.get("thumb"),
            "tags": ["cheapshark", "gaming", "source-price"],
        }
        item["score"] = deal_score(item)
        deals.append(finalize_item(item))
    return deals


def rss_child_text(parent: ElementTree.Element, names: tuple[str, ...]) -> str:
    for child in parent:
        tag = child.tag.split("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text
    return ""


def rss_link(parent: ElementTree.Element) -> str:
    for child in parent:
        tag = child.tag.split("}", 1)[-1].lower()
        if tag != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href
        if child.text:
            return child.text
    guid = rss_child_text(parent, ("guid", "id"))
    return guid


def normalize_rss_item(source: str, entry: ElementTree.Element) -> dict:
    title = clean_text(rss_child_text(entry, ("title",)))
    link = clean_text(rss_link(entry), 1000)
    summary = clean_text(rss_child_text(entry, ("description", "summary", "content")), 700)
    published_at = parse_datetime(rss_child_text(entry, ("pubdate", "published", "updated", "date")))
    price_signal = parse_price_signal(f"{title} {summary}")
    category = detect_category(title, summary, domain_from_url(link) or "")
    item = {
        "id": stable_id(source, title, link),
        "source": source,
        "source_item_id": None,
        "item_type": SOURCE_METADATA[source]["item_type"],
        "title": title,
        "summary": summary,
        "deal_url": link,
        "source_url": SOURCE_METADATA[source]["source_url"],
        "published_at": published_at,
        "merchant": domain_from_url(link),
        "category": category,
        "price": price_signal["price"],
        "currency": price_signal["currency"],
        "normal_price": None,
        "discount_percent": price_signal["discount_percent"],
        "price_confidence": price_signal["price_confidence"],
        "is_live_price": price_signal["price"] is not None,
        "real_time_inventory": False,
    }
    item["tags"] = build_tags(title, category, source)
    item["score"] = deal_score(item)
    return finalize_item(item)


def fetch_rss_source(source: str, limit: int = 40) -> list[dict]:
    response = http_get(SOURCE_METADATA[source]["source_url"])
    root = ElementTree.fromstring(response.content)
    entries = list(root.findall(".//item"))
    if not entries:
        entries = [
            entry
            for entry in root.iter()
            if entry.tag.split("}", 1)[-1].lower() == "entry"
        ]
    deals = []
    seen: set[str] = set()
    for entry in entries:
        item = normalize_rss_item(source, entry)
        if item["title"] and item["deal_url"] and item["id"] not in seen:
            seen.add(item["id"])
            deals.append(item)
        if len(deals) >= limit:
            break
    return deals


def fetch_hn_algolia(limit: int = 40) -> list[dict]:
    queries = ["discount OR deal", "coupon", "pricing", "AI tool", "hosting", "course"]
    deals = []
    seen: set[str] = set()
    per_query = max(5, min(20, limit // len(queries) + 1))
    for query in queries:
        response = http_get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": query, "tags": "story", "hitsPerPage": str(per_query)},
        )
        for hit in response.json().get("hits", []):
            title = clean_text(hit.get("title") or hit.get("story_title"))
            url = clean_text(
                hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                1000,
            )
            item_id = stable_id("hn_algolia", title, url)
            if item_id in seen:
                continue
            seen.add(item_id)
            summary = clean_text(
                f"Hacker News discussion by {hit.get('author')} with {hit.get('num_comments', 0)} comments."
            )
            price_signal = parse_price_signal(title)
            category = detect_category(title, url, summary)
            item = {
                "id": item_id,
                "source": "hn_algolia",
                "source_item_id": hit.get("objectID"),
                "item_type": "market_signal",
                "title": title,
                "summary": summary,
                "deal_url": url,
                "source_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "published_at": parse_datetime(hit.get("created_at")),
                "merchant": domain_from_url(url),
                "category": category,
                "price": price_signal["price"],
                "currency": price_signal["currency"],
                "normal_price": None,
                "discount_percent": price_signal["discount_percent"],
                "price_confidence": price_signal["price_confidence"],
                "is_live_price": False,
                "real_time_inventory": False,
            }
            item["tags"] = build_tags(title, category, "hn_algolia")
            item["score"] = deal_score(item)
            deals.append(finalize_item(item))
            if len(deals) >= limit:
                return deals
    return deals


def fetch_github_resources(limit: int = 20) -> list[dict]:
    queries = [
        "awesome black friday cyber monday deals stars:>50",
        "deals discounts coupons stars:>25",
        "student developer pack discounts stars:>25",
    ]
    resources = []
    seen: set[str] = set()
    per_query = max(5, min(20, limit // len(queries) + 1))
    for query in queries:
        response = http_get(
            SOURCE_METADATA["github_resources"]["source_url"],
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": str(per_query),
            },
        )
        for repo in response.json().get("items", []):
            title = clean_text(repo.get("full_name"))
            url = clean_text(repo.get("html_url"), 1000)
            item_id = stable_id("github_resources", title, url)
            if item_id in seen:
                continue
            seen.add(item_id)
            summary = clean_text(repo.get("description") or "Curated deal and discount resource list.")
            category = detect_category(title, summary)
            item = {
                "id": item_id,
                "source": "github_resources",
                "source_item_id": repo.get("id"),
                "item_type": "resource_list",
                "title": title,
                "summary": summary,
                "deal_url": url,
                "source_url": SOURCE_METADATA["github_resources"]["source_url"],
                "published_at": parse_datetime(repo.get("updated_at")),
                "merchant": "github.com",
                "category": category,
                "price": None,
                "currency": None,
                "normal_price": None,
                "discount_percent": None,
                "price_confidence": "not_detected",
                "is_live_price": False,
                "real_time_inventory": False,
                "tags": build_tags(title, category, "github_resources"),
            }
            item["score"] = deal_score(item)
            resources.append(finalize_item(item))
            if len(resources) >= limit:
                return resources
    return resources


def fetch_source(source: str) -> list[dict]:
    if source == "cheapshark":
        return fetch_cheapshark()
    if source in RSS_SOURCE_NAMES:
        return fetch_rss_source(source)
    if source == "hn_algolia":
        return fetch_hn_algolia()
    if source == "github_resources":
        return fetch_github_resources()
    raise ValueError(f"Unsupported source: {source}")


def refresh_deals(force: bool = False) -> dict:
    with cache_lock:
        updated_at = cache["metadata"].get("updated_at")
        if not force and updated_at:
            try:
                last_update = datetime.fromisoformat(updated_at)
                if time.time() - last_update.timestamp() < CACHE_TTL_SECONDS:
                    return {"status": "cached", "metadata": cache["metadata"]}
            except ValueError:
                pass

    if not refresh_lock.acquire(blocking=False):
        with cache_lock:
            return {"status": "refresh_in_progress", "metadata": cache["metadata"]}

    try:
        fetched_at = now_iso()
        source_errors = {}
        all_deals: list[dict] = []
        for source in sorted(ENABLED_SOURCES):
            if source not in SOURCE_METADATA:
                source_errors[source] = "source is not configured"
                continue
            try:
                all_deals.extend(fetch_source(source))
            except Exception as exc:  # pragma: no cover - exact network failures vary.
                source_errors[source] = f"{type(exc).__name__}: {exc}"

        seen: set[str] = set()
        deduped = []
        for item in sorted(all_deals, key=lambda deal: deal.get("score", 0), reverse=True):
            key = normalize_text(f"{item.get('title')} {item.get('deal_url')}")
            if key not in seen:
                seen.add(key)
                deduped.append(item)

        with cache_lock:
            if deduped:
                cache["deals"] = deduped
                cache["metadata"] = {
                    "api": APP_NAME,
                    "version": APP_VERSION,
                    "updated_at": fetched_at,
                    "last_successful_refresh_at": fetched_at,
                    "deal_count": len(deduped),
                    "sources": sorted(
                        {item["source"] for item in deduped}
                    ),
                    "source_errors": source_errors,
                    "cache_ttl_seconds": CACHE_TTL_SECONDS,
                }
                return {"status": "updated", "metadata": cache["metadata"]}
            cache["metadata"]["updated_at"] = fetched_at
            cache["metadata"]["source_errors"] = source_errors
            return {"status": "failed", "metadata": cache["metadata"]}
    finally:
        refresh_lock.release()


def snapshot(force: bool = False) -> dict:
    refresh_deals(force=force)
    with cache_lock:
        return {"deals": list(cache["deals"]), "metadata": dict(cache["metadata"])}


def parse_limit_offset() -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
    return max(1, min(MAX_LIMIT, limit)), max(0, offset)


def filter_deals(deals: list[dict]) -> list[dict]:
    q = normalize_text(request.args.get("q", ""))
    category = request.args.get("category", "").strip().lower()
    source = request.args.get("source", "").strip().lower()
    item_type = request.args.get("item_type", "").strip().lower()
    try:
        min_score = int(request.args.get("min_score", "0"))
    except ValueError:
        min_score = 0

    filtered = []
    for item in deals:
        searchable = normalize_text(
            " ".join(
                [
                    item.get("title", ""),
                    item.get("summary", ""),
                    item.get("merchant") or "",
                    " ".join(item.get("tags", [])),
                ]
            )
        )
        if q and q not in searchable:
            continue
        if category and item.get("category") != category:
            continue
        if source and item.get("source") != source:
            continue
        if item_type and item.get("item_type") != item_type:
            continue
        if int(item.get("score", 0)) < min_score:
            continue
        filtered.append(item)

    sort = request.args.get("sort", "score").strip().lower()
    if sort == "newest":
        filtered.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    elif sort == "price":
        filtered.sort(key=lambda item: (item.get("price") is None, item.get("price") or 0))
    elif sort == "discount":
        filtered.sort(key=lambda item: item.get("discount_percent") or 0, reverse=True)
    else:
        filtered.sort(key=lambda item: item.get("score", 0), reverse=True)
    return filtered


def counts_by(items: list[dict], field: str) -> dict:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(field) or "unknown"
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[1], reverse=True))


@app.get("/health")
def health():
    with cache_lock:
        metadata = dict(cache["metadata"])
    return jsonify(
        {
            "status": "ok",
            "api": APP_NAME,
            "version": APP_VERSION,
            "cache": metadata,
            "paid_gateway_required": os.environ.get("REQUIRE_PAID_GATEWAY", "true").lower()
            in {"1", "true", "yes"},
        }
    )


@app.get("/")
def index():
    return jsonify(
        {
            "api": APP_NAME,
            "version": APP_VERSION,
            "message": "Paid global deal radar for applications, newsletters, dashboards and AI agents.",
            "endpoints": ["/deals", "/trending", "/categories", "/sources", "/stats", "/search-links"],
        }
    )


@app.get("/deals")
def deals():
    data = snapshot(force=request.args.get("refresh", "").lower() in {"1", "true", "yes"})
    filtered = filter_deals(data["deals"])
    limit, offset = parse_limit_offset()
    return jsonify(
        {
            "metadata": {
                **data["metadata"],
                "total": len(data["deals"]),
                "matched": len(filtered),
                "count": len(filtered[offset : offset + limit]),
                "limit": limit,
                "offset": offset,
            },
            "deals": filtered[offset : offset + limit],
        }
    )


@app.get("/deals/<deal_id>")
def deal_detail(deal_id: str):
    data = snapshot()
    for item in data["deals"]:
        if item["id"] == deal_id:
            return jsonify({"deal": item, "metadata": data["metadata"]})
    return jsonify({"error": "Deal not found"}), 404


@app.get("/trending")
def trending():
    data = snapshot(force=request.args.get("refresh", "").lower() in {"1", "true", "yes"})
    category = request.args.get("category", "").strip().lower()
    deals = filter_deals(data["deals"])
    if category:
        deals = [item for item in deals if item.get("category") == category]
    limit, offset = parse_limit_offset()
    return jsonify(
        {
            "metadata": {
                **data["metadata"],
                "category": category or "all",
                "matched": len(deals),
                "count": len(deals[offset : offset + limit]),
                "limit": limit,
                "offset": offset,
            },
            "deals": deals[offset : offset + limit],
        }
    )


@app.get("/categories")
def categories():
    data = snapshot()
    counts = counts_by(data["deals"], "category")
    return jsonify(
        {
            "metadata": data["metadata"],
            "categories": [
                {
                    "id": category,
                    "name": category.replace("-", " ").title(),
                    "description": description,
                    "count": counts.get(category, 0),
                }
                for category, description in CATEGORY_DEFINITIONS.items()
            ],
        }
    )


@app.get("/sources")
def sources():
    data = snapshot()
    active_counts = counts_by(data["deals"], "source")
    return jsonify(
        {
            "metadata": data["metadata"],
            "sources": [
                {
                    "id": source,
                    **details,
                    "enabled": source in ENABLED_SOURCES,
                    "active_item_count": active_counts.get(source, 0),
                    "latest_error": data["metadata"].get("source_errors", {}).get(source),
                }
                for source, details in SOURCE_METADATA.items()
            ],
        }
    )


@app.get("/stats")
def stats():
    data = snapshot()
    return jsonify(
        {
            "metadata": data["metadata"],
            "stats": {
                "total_items": len(data["deals"]),
                "by_category": counts_by(data["deals"], "category"),
                "by_source": counts_by(data["deals"], "source"),
                "by_item_type": counts_by(data["deals"], "item_type"),
                "priced_items": sum(1 for item in data["deals"] if item.get("price") is not None),
                "source_price_items": sum(
                    1 for item in data["deals"] if item.get("price_confidence") == "source_provided"
                ),
            },
        }
    )


@app.get("/search-links")
def search_links():
    q = clean_text(request.args.get("q") or "best deals", 80)
    encoded = quote_plus(q)
    links = [
        {"provider": "Google Shopping", "category": "shopping", "url": f"https://www.google.com/search?tbm=shop&q={encoded}"},
        {"provider": "Slickdeals", "category": "shopping", "url": f"https://slickdeals.net/newsearch.php?q={encoded}"},
        {"provider": "Google Flights", "category": "travel", "url": f"https://www.google.com/travel/flights?q={encoded}"},
        {"provider": "Booking", "category": "travel", "url": f"https://www.booking.com/searchresults.html?ss={encoded}"},
        {"provider": "AppSumo", "category": "software", "url": f"https://appsumo.com/search/?query={encoded}"},
        {"provider": "Product Hunt", "category": "software", "url": f"https://www.producthunt.com/search?q={encoded}"},
        {"provider": "Udemy", "category": "courses", "url": f"https://www.udemy.com/courses/search/?q={encoded}"},
        {"provider": "Audible", "category": "books-audiobooks", "url": f"https://www.audible.com/search?keywords={encoded}"},
        {"provider": "GitHub", "category": "digital-products", "url": f"https://github.com/search?q={encoded}&type=repositories"},
    ]
    category = request.args.get("category", "").strip().lower()
    if category:
        links = [link for link in links if link["category"] == category]
    return jsonify({"query": q, "count": len(links), "links": links})


@app.get("/openapi.json")
def openapi_schema():
    return jsonify(
        {
            "openapi": "3.1.0",
            "info": {
                "title": APP_NAME,
                "version": APP_VERSION,
                "description": "Paid global deal radar with normalized deals, market signals, categories, source attribution and search links.",
            },
            "servers": [{"url": "https://global-deal-radar-api.onrender.com"}],
            "paths": {
                "/health": {"get": {"summary": "Public health check"}},
                "/deals": {"get": {"summary": "List normalized deals and opportunity signals"}},
                "/deals/{deal_id}": {"get": {"summary": "Get one deal by id"}},
                "/trending": {"get": {"summary": "Top-scored deals and signals"}},
                "/categories": {"get": {"summary": "Deal categories with counts"}},
                "/sources": {"get": {"summary": "Source metadata, attribution and status"}},
                "/stats": {"get": {"summary": "Deal counts by category, source and item type"}},
                "/search-links": {"get": {"summary": "Provider search links for follow-up research"}},
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
