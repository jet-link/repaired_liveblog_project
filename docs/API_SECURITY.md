# Blog HTTP API — authentication, CSRF, rate limits

Base path: `/blog/` (see [smart_blog/urls.py](/liveblog_project/smart_blog/urls.py)).

All browser-initiated **state-changing** requests must include the **CSRF** cookie and header/token expected by `CsrfViewMiddleware`. JSON POST endpoints use the standard CSRF header (`X-CSRFToken` or `X-CSRFTOKEN`).

| Endpoint | Methods | Auth | CSRF (session cookie) | Application rate limit (IP unless noted) |
|----------|---------|------|----------------------|-------------------------------------------|
| `api/report/post/<pk>/` | GET | Login | N/A (safe) | 90/m |
| `api/report/comment/<pk>/` | GET | Login | N/A | 90/m |
| `report/post/<pk>/` | POST | Login | Yes | `RATELIMIT_REPORT_POST_RATE` (default 40/m) |
| `report/comment/<pk>/` | POST | Login | Yes | same as row above |
| `report/<pk>/delete/` | DELETE/POST | Login | Yes | (reuse report service limits) |
| `api/post/<post_id>/counters/` | GET | No | N/A | `RATELIMIT_ITEM_COUNTERS_RATE` (default 90/m) |
| `api/repost/` | POST | No | Yes | 30/m (+ per-item cooldowns in code) |
| `api/search-suggest/` | GET | No | N/A | `RATELIMIT_SEARCH_SUGGEST_RATE` (default 60/m) |
| `api/search-history/` | GET | Login | N/A | `RATELIMIT_SEARCH_HISTORY_RATE` |
| `api/search-history/<pk>/clicked/` | POST | Login | Yes | same as search-history rate |
| `api/search-history/clear/` | POST | Login | Yes | same as search-history rate |
| `api/search-history/<pk>/delete/` | POST | Login | Yes | same as search-history rate |
| `api/trending/` | GET | No | N/A | `RATELIMIT_TRENDING_RATE` (default 120/m) |

Global search page `/search/` (GET): `RATELIMIT_SEARCH_RATE` (default 60/m per IP), returns HTTP 429 page when exceeded.

Search overlay autocomplete `api/search-suggest/?q=…` returns up to 10 published post titles + item URLs (FTS); empty `items` when query is shorter than 2 characters. Rate limited per IP.

**Note:** Limits depend on Django’s cache backend. Use **Redis** in production so limits are enforced across multiple worker processes.
