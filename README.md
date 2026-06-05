# GlobalDealRadarAPI

Paid global deal intelligence API for apps, newsletters, dashboards and AI
agents that need a low-cost hook product with real public deal signals.

It normalizes live deal feeds, community deal posts and market signals into one
contract with categories, price extraction, scoring, source attribution and
safe follow-up search links.

## What It Covers

- Shopping and consumer deals
- Electronics and hardware bargains
- Software, SaaS, AI tools and productivity offers
- Courses, training and certifications
- Game deals with source-provided prices through CheapShark
- Travel, flights, hotels, luggage and package search routes
- Hosting, domains, cloud, VPN and infrastructure opportunities
- Books, audiobooks, recipes and cookbook-related deal discovery
- Digital products, templates, assets and business tools
- Popular curated deal resources and developer-facing market signals

## Data Sources

| Source | Type | Notes |
| --- | --- | --- |
| CheapShark | Public API | Source-provided game sale price, normal price, savings and redirect URL |
| Slickdeals | RSS | Frontpage community deal posts |
| DealNews | RSS | Editorial daily deal posts |
| TechBargains | RSS | Technology bargain posts |
| Reddit r/deals | RSS | Community deal discussions |
| Hacker News Algolia | Public API | Software, AI, hosting and pricing market signals |
| GitHub Search | Public API | Popular curated discount-resource repositories |

The API does not claim ownership of third-party listings. Keep original URLs
and source attribution visible in downstream products.

## Access Model

Only `/health` and `/openapi.json` are public. Product data endpoints require a
gateway secret sent by RapidAPI or another paid marketplace:

- `X-RapidAPI-Proxy-Secret`
- `X-API-Gateway-Secret`
- `X-GlobalDealRadarAPI-Secret`

Direct backend calls without the configured secret receive `402 Payment
Required`.

## Endpoints

### `GET /health`

Public runtime status and cache metadata.

### `GET /deals`

Normalized deal and opportunity feed.

Query parameters:

- `q`: text search across title, summary, merchant and tags
- `category`: one category id, such as `software`, `ai-tools`, `travel`,
  `books-audiobooks`, `food-recipes` or `gaming`
- `source`: one source id, such as `cheapshark` or `slickdeals`
- `item_type`: `deal`, `market_signal` or `resource_list`
- `min_score`: minimum score from 1 to 100
- `sort`: `score`, `newest`, `discount` or `price`
- `limit`: 1 to 100
- `offset`: pagination offset
- `refresh`: `true` to force a refresh

### `GET /deals/{deal_id}`

Single normalized deal by id.

### `GET /trending`

Top-scored deals and signals.

### `GET /categories`

Category catalog with current counts.

### `GET /sources`

Source metadata, active counts and latest source errors.

### `GET /stats`

Counts by category, source and item type.

### `GET /search-links`

Useful paid-customer follow-up search links for a query. This endpoint is not a
scraper; it helps users continue research through major providers.

## Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
REQUIRE_PAID_GATEWAY=false python server.py
```

Run tests:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Render

Use the included `render.yaml` Blueprint. The default service is configured for
Render's free web service plan and paid-gateway protection.

The generated plaintext gateway secret for this workspace is stored outside the
repository at:

```text
~/.config/patoapis/global_deal_radar_gateway_secret
```

Do not commit or publish that secret. Configure RapidAPI to send the same value
as `X-RapidAPI-Proxy-Secret`.

## Suggested RapidAPI Positioning

Title:

```text
Global Deal Radar API
```

Short description:

```text
Paid global deal intelligence for shopping, software, AI tools, courses,
gaming, travel, hosting, books, audiobooks, recipes and digital products.
```

Long description:

```text
GlobalDealRadarAPI gives builders a single paid API for worldwide deal
discovery. It combines public deal APIs, RSS feeds, community deal posts,
developer-market signals and curated resource discovery into one normalized
contract with scoring, categories, price extraction, source attribution and
filtering.

Use it to power newsletters, personal finance apps, shopping dashboards,
browser extensions, AI agents, SaaS lead magnets, travel assistants, gaming
deal apps, course-deal trackers and digital product discovery tools.

Plans should be priced low enough to work as a hook product while still keeping
all product data behind the paid marketplace gateway.
```

Suggested starting price:

- Basic: USD 2.99/month, low request quota
- Pro: USD 9.99/month, higher quota
- Ultra: USD 29.99/month, commercial quota

No free public data endpoint is included.
