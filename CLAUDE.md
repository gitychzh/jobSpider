# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Run 51job scraper locally: `python -m scrapers.runner --source job51`
- Run scraper and push to D1: `python -m scrapers.runner --source job51 --push-d1`
- Control page count: `python -m scrapers.runner --source job51 --pages 10`
- Local preview frontend: `cd web && python -m http.server 8081` → visit http://localhost:8081
- Install dependencies: `pip install -r requirements.txt && playwright install chromium --with-deps`
- Deploy Worker API: `cd worker && CLOUDFLARE_API_TOKEN=<token> wrangler deploy`
- Deploy frontend to Pages: `cd web && CLOUDFLARE_API_TOKEN=<token> wrangler pages deploy . --project-name=jobspider --branch=main`

## Deployment Architecture (Cloudflare)

This project uses **Cloudflare free-tier services** instead of GitHub Pages:

- **Cloudflare Pages** (`jobspider.pages.dev`): hosts the static frontend (`web/` content)
- **Cloudflare Worker** (`jobspider-api`): API that reads/writes D1, serves job data to frontend
  - Worker URL: `https://jobspider-api.93921526.workers.dev`
  - Routes: `/api/jobs`, `/api/stats`, `/api/sources`, `/api/cities`, `/api/import`, `/api/cleanup`
- **Cloudflare D1** (`jobSpider-db`, UUID: `9167c8e5-d910-4bd7-bba4-a2bea611cd4f`): SQLite database storing all job data
  - Tables: `jobs` (primary data), `scrape_runs` (history log)
  - Free tier: 5M rows read/day, 100K rows written/day, 5GB storage
- **GitHub Actions** (`scrape.yml`): daily scraper runs, pushes results to D1 via `/api/import`

Frontend fetches data from the Worker API, not from static JSON files. The `API_BASE` constant in `web/js/app.js` points to the Worker URL.

**Import API authentication**: `/api/import` requires `X-Import-Secret` header. Secret is `jobSpider2024secret` (set in `worker/wrangler.toml` `[vars]`). GitHub Actions uses `CF_IMPORT_SECRET` env var.

## Architecture

**Data flow**: scraper → `/api/import` → D1 → `/api/jobs` → frontend SPA

**Scraper framework** (`scrapers/`):
- `base.py`: `BaseScraper` abstract class. Subclasses implement `name`, `display_name`, `scrape()`. Provides `save_json()` (local backup), `save_to_d1()` (push to D1 via API), `generate_stats()`.
- `runner.py`: CLI entrypoint, orchestrates scrapers. `--push-d1` flag sends data to Worker API.
- Each platform is a sub-package inheriting `BaseScraper`
- JobDict fields: `job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, confirm_date, update_time, job_url, city, scrape_date, source`

**51job scraper** (`scrapers/job51/`):
- Uses Playwright to bypass Alibaba Cloud WAF, then calls API via `page.evaluate(JS_FETCH_API)` inside browser context
- Single browser page for all cities to avoid WAF re-verification

**Worker API** (`worker/api/index.js`):
- Reads from D1 with pagination, filtering, sorting
- `/api/import` endpoint for external scraper to push data (auth: X-Import-Secret header)
- `/api/cleanup` endpoint to remove old data (keep_days parameter)
- CORS enabled for cross-origin access from Pages

**Frontend** (`web/`):
- Pure SPA, no build step, no framework
- `app.js`: fetches from Worker API, handles search/filter/pagination via query params
- `render.js`: job cards, stats panel, pagination, source tags

**Adding a new platform scraper**:
1. Create `scrapers/<platform>/` with class inheriting `BaseScraper`
2. Register in `runner.py`'s `get_available_scrapers()`
3. Add to `AVAILABLE_SOURCES` in `app.js` and add tab button in `index.html`

## Cloudflare Account Info

- Account ID: `fcd03f4fb32acc1f7073a1fd13645fe6`
- D1 database: `jobSpider-db` / `9167c8e5-d910-4bd7-bba4-a2bea611cd4f`
- Pages project: `jobspider` → `jobspider.pages.dev`
- Worker: `jobspider-api` → `jobspider-api.93921526.workers.dev`

## Key Design Decisions

- D1 replaces static JSON files — enables real-time data, filtering/sorting on server side, no CDN stale cache issues
- 51job WAF bypass still requires Playwright (Python), so scraper runs outside CF Workers
- GitHub Actions remains the cron trigger since CF Workers Cron can't run Playwright
- Local JSON files kept as backup (`save_json()` still runs)
- Remote uses SSH on port 443 (`ssh.github.com`) since port 22 is blocked

## Common Issues

- **WAF blocking**: if scraper returns 0 jobs, WAF may have blocked the browser. Re-run; Playwright stealth helps but isn't guaranteed
- **API_BASE mismatch**: if Worker URL changes, update `API_BASE` in `web/js/app.js` and redeploy Pages