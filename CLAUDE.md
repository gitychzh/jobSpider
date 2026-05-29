# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Run 51job scraper: `python3 -m scrapers.runner --source job51`
- Run all scrapers: `python3 -m scrapers.runner`
- Control page count: `python3 -m scrapers.runner --source job51 --pages 10`
- Local preview frontend: `cd web && python3 -m http.server 8081` → visit http://localhost:8081
- Install dependencies: `pip3 install -r requirements.txt && playwright install chromium --with-deps`

## Deployment

This project deploys via **GitHub Pages** using a two-branch strategy:
- `cc2` (or default branch): source code (scrapers + web source)
- `gh-pages`: deployed static site (only `web/` content at root)

**Deploying after frontend changes**: checkout `gh-pages`, copy updated files from `web/` to branch root, commit & push:
```
git checkout gh-pages
rm js/app.js js/render.js css/style.css index.html
git show cc2:web/index.html > index.html
mkdir -p css js data
git show cc2:web/css/style.css > css/style.css
git show cc2:web/js/app.js > js/app.js
git show cc2:web/js/render.js > js/render.js
git add -A && git commit -m "update" && git push
git checkout cc2
```

**Deploying after scraper run (data update)**: same process but also copy `web/data/*.json` files.

**GitHub Actions** (`scrape.yml`): runs scraper daily at UTC 02:00 and deploys via official `deploy-pages@v4` action. Requires GitHub Pages source set to "GitHub Actions" in Settings > Pages.

## Architecture

This project uses a **static-site architecture** for GitHub Pages:
- Scrapers output JSON to `web/data/` (no database)
- Frontend is pure HTML/CSS/JS SPA that fetches JSON — no backend server
- Data flow: scraper → JSON files → gh-pages branch → GitHub Pages CDN

**Scraper framework** (`scrapers/`):
- `base.py`: `BaseScraper` abstract class. Subclasses must implement `name`, `display_name`, `scrape()` → `List[JobDict]`. Provides `save_json()` and `generate_stats()`.
- `runner.py`: CLI entrypoint, orchestrates all scrapers, writes JSON output to `web/data/`
- Each platform is a sub-package inheriting `BaseScraper`
- JobDict fields: `job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, confirm_date, update_time, job_url, city, scrape_date, source`

**51job scraper** (`scrapers/job51/`):
- **Critical**: does NOT use `requests` — the 51job API has Alibaba Cloud WAF that blocks plain HTTP requests
- Uses Playwright to open one search page (bypass WAF), then calls the API via `page.evaluate(JS_FETCH_API)` inside the browser context
- Strategy: visit search page once → WAF passes → all subsequent API calls via JS fetch in same browser page
- `browser.py`: manages Playwright instance lifecycle (`ensure_browser`, `close_browser`)
- `config.py`: city codes, API base URL, `ApiParams` dataclass for building query params

**Frontend** (`web/`):
- Pure SPA, no build step, no framework
- `app.js`: data loading, city filter, sort (issue_date/confirm_date/update_time, desc/asc), pagination
- `render.js`: job cards, stats panel, pagination, source tags, coming-soon placeholder
- Sort and city filter are client-side against cached JSON data
- `updateCityFilter()` must be called AFTER data loads into cache — not before

**Adding a new platform scraper**:
1. Create `scrapers/<platform>/` with class inheriting `BaseScraper`
2. Register in `runner.py`'s `get_available_scrapers()`
3. Create `web/data/<platform>.json` placeholder
4. Add to `AVAILABLE_SOURCES` in `app.js` and add a tab button in `index.html`

## Key Design Decisions

- No SQLite/database — data lives in JSON files for static-site compatibility
- 51job API bypasses WAF by using Playwright JS fetch (not Python requests)
- Single browser page for all cities — avoids WAF re-verification per city
- GitHub Pages CDN cache: `max-age=600` (10 min), data updates may take ~10 min to appear
- Remote uses SSH on port 443 (`ssh.github.com`) since port 22 is blocked

## Common Issues

- **WAF blocking**: if scraper returns 0 jobs, WAF may have blocked the browser. Try re-running; Playwright stealth mode helps but is not guaranteed
- **CDN stale data**: after pushing to gh-pages, data may show old values for ~10 minutes due to CDN cache
- **City dropdown empty**: `updateCityFilter` must run after `loadSourceData` completes, not before