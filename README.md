# GlobalDealRadarAPI

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Product](https://img.shields.io/badge/Product-Page-blue.svg)](https://patoapis-paid-apis.onrender.com/global-deal-radar-api.html)

**🔍 Global deal intelligence API for apps, newsletters, dashboards and AI agents**

[View product details](https://patoapis-paid-apis.onrender.com/global-deal-radar-api.html?utm_source=github&utm_medium=repository&utm_campaign=globaldeals_readme) |
[Live Demo](https://patoapis-paid-apis.onrender.com/)

> Commercial API access is designed for marketplace-managed credentials and
> protected production usage.

GlobalDealRadarAPI normalizes live deal feeds, community deal posts and market signals into one contract with categories, price extraction, scoring, source attribution and safe follow-up search links.

**Perfect for:**
- Deal newsletters and RSS feeds
- Shopping comparison apps
- Personal finance dashboards
- Browser extensions
- AI-powered deal assistants
- SaaS lead magnets

## ✨ Key Features

- **🛒 Shopping Deals**: Consumer discounts and bargains across categories
- **💻 Software & SaaS**: Productivity tools, AI services, and software offers
- **🎮 Gaming**: Game deals with source-provided prices via CheapShark
- **✈️ Travel**: Flights, hotels, luggage and package search routes
- **☁️ Infrastructure**: Hosting, domains, cloud, VPN and infrastructure deals
- **📚 Digital Content**: Books, audiobooks, recipes and cookbook-related deals
- **📊 Market Signals**: Developer-facing market signals from Hacker News and GitHub
- **🏷️ Price Extraction**: Automatic price and discount detection
- **📈 Scoring System**: Deal quality scoring from 1-100
- **🔗 Source Attribution**: Transparent source tracking and compliance

## 📡 Data Sources

| Source | Type | Notes |
| --- | --- | --- |
| **CheapShark** | Public API | Game sale price, normal price, savings and redirect URL |
| **Slickdeals** | RSS | Frontpage community deal posts |
| **DealNews** | RSS | Editorial daily deal posts |
| **TechBargains** | Optional RSS | Technology bargain posts (disabled by default on some hosts) |
| **Reddit r/deals** | Optional RSS | Community deal discussions (disabled by default on some hosts) |
| **Hacker News Algolia** | Public API | Software, AI, hosting and pricing market signals |
| **GitHub Search** | Public API | Popular curated discount-resource repositories |

The API keeps original URLs and source attribution available so downstream
products can show transparent deal provenance.

## Access Model

`/health` and `/openapi.json` expose only operational and documentation
metadata. Product data endpoints require a gateway secret sent by RapidAPI or
another paid marketplace:

- `X-RapidAPI-Proxy-Secret`
- `X-API-Gateway-Secret`
- `X-GlobalDealRadarAPI-Secret`

Production requests are designed to flow through authorized marketplace
credentials.

## 🛠️ API Endpoints

### `GET /health`
Public runtime status and cache metadata.

### `GET /deals`
Normalized deal and opportunity feed.

**Query Parameters:**
- `q`: Text search across title, summary, merchant and tags
- `category`: Filter by category (`software`, `ai-tools`, `travel`, `books-audiobooks`, `food-recipes`, `gaming`)
- `source`: Filter by source (`cheapshark`, `slickdeals`, `dealnews`)
- `item_type`: Filter by type (`deal`, `market_signal`, `resource_list`)
- `min_score`: Minimum score from 1 to 100
- `sort`: Sort order (`score`, `newest`, `discount`, `price`)
- `limit`: Results per page (1-100)
- `offset`: Pagination offset
- `refresh`: Force a refresh (`true`)

### `GET /deals/{deal_id}`
Single normalized deal by ID.

### `GET /trending`
Top-scored deals and signals.

### `GET /categories`
Category catalog with current counts.

### `GET /sources`
Source metadata, active counts and latest source errors.

### `GET /stats`
Counts by category, source and item type.

### `GET /search-links`
Useful paid-customer follow-up search links for a query.

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/patoalba2019/global-deal-radar-api.git
cd global-deal-radar-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server with paid-gateway protection enabled
python server.py
```

### Test the API
```bash
# Health check
curl http://localhost:5000/health

# Product data requires the configured marketplace gateway secret
curl "http://localhost:5000/deals?limit=10&category=software" \
  -H "X-RapidAPI-Proxy-Secret: $GATEWAY_SECRET"

# Get trending deals
curl http://localhost:5000/trending
```

## 🌐 Deployment

### Render (Recommended)
Use the included `render.yaml` Blueprint. The default service is configured for
lightweight cloud hosting and paid-gateway protection.

### Environment Variables for Production
```bash
PORT=5000
REQUIRE_PAID_GATEWAY=true
PAID_GATEWAY_SECRET_HASHES=<your-hash>
ENABLED_SOURCES=cheapshark,slickdeals,dealnews,hn_algolia,github_resources
CACHE_TTL_SECONDS=1800
```

## 📈 Pricing

### RapidAPI Plans
- **Basic**: $2.99/month - Low request quota (hook product)
- **Pro**: $9.99/month - Higher quota
- **Ultra**: $29.99/month - Commercial quota

[View product details](https://patoapis-paid-apis.onrender.com/global-deal-radar-api.html)

## 📊 Use Cases

- **Deal Newsletters**: Power automated deal digest emails
- **Shopping Apps**: Build comparison and deal-finding applications
- **Personal Finance**: Track deals and savings opportunities
- **Browser Extensions**: Add deal alerts to web browsers
- **AI Assistants**: Feed deal data to AI-powered shopping assistants
- **SaaS Lead Magnets**: Use deal data as a content marketing tool
- **Gaming Apps**: Track game deals and price drops
- **Course Trackers**: Monitor online course discounts

## 🔗 Links

- [Product Website](https://patoapis-paid-apis.onrender.com/global-deal-radar-api.html)
- [Live Health](https://global-deal-radar-api.onrender.com/health)

## Suggested Marketplace Positioning

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

Production product data is designed for paid marketplace access.
