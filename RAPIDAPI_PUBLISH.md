# RapidAPI Publish Checklist

## API Basics

- Name: `GlobalDealRadarAPI`
- Category: Data / eCommerce / Tools
- Base URL: `https://global-deal-radar-api.onrender.com`
- Authentication shown to customers: RapidAPI key only
- Backend protection: set RapidAPI to send `X-RapidAPI-Proxy-Secret`

## Private Backend Secret

The plaintext secret is stored locally, outside git:

```text
~/.config/patoapis/global_deal_radar_gateway_secret
```

Use that value only inside RapidAPI gateway configuration. Never paste it into
public docs, screenshots, README examples, marketplace descriptions or support
messages.

## Recommended Endpoints

| Endpoint | Visibility | Purpose |
| --- | --- | --- |
| `GET /health` | Public | Health check |
| `GET /deals` | Paid | Normalized deal feed |
| `GET /deals/{deal_id}` | Paid | Single deal detail |
| `GET /trending` | Paid | Top-scored opportunities |
| `GET /categories` | Paid | Category catalog and counts |
| `GET /sources` | Paid | Source metadata and attribution |
| `GET /stats` | Paid | Feed analytics |
| `GET /search-links` | Paid | Provider follow-up search links |

## Marketplace Copy

### Tagline

```text
Worldwide deal discovery for apps, newsletters, dashboards and AI agents.
```

### Description

```text
GlobalDealRadarAPI normalizes public deal feeds, community deal posts, game
price APIs, developer-market signals and curated deal resources into one paid
API. Filter by category, source, keyword, score and item type, then use
standardized fields for title, URL, merchant, price signals, discount,
attribution, tags and deal score.

Ideal for shopping apps, AI assistants, browser extensions, newsletters,
travel-deal projects, course trackers, gaming deal dashboards, software-deal
tools and digital-product discovery products.
```

### Customer Promise

```text
One API contract for many deal categories. No direct backend access. Source
URLs and attribution included.
```

## Suggested Pricing

Keep the product cheap enough to attract first buyers:

- Basic: USD 2.99/month
- Pro: USD 9.99/month
- Ultra: USD 29.99/month

Use request quotas low enough that heavy commercial users naturally upgrade.

## Security Check

Before publishing:

```bash
curl -i https://global-deal-radar-api.onrender.com/deals
```

Expected result: `402 Payment Required`.

Then test through RapidAPI. Expected result: `200 OK`.
