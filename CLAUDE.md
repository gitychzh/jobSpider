# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Run 51job scraper: `python -m scrapers.runner --source job51`
- Run all scrapers: `python -m scrapers.runner`
- Control page count: `python -m scrapers.runner --source job51 --pages 10`
- Local preview frontend: `cd web && python -m http.server 8081`
- Install dependencies: `pip install -r requirements.txt && playwright install chromium --with-deps`

## Architecture

This project uses a **static-site architecture** for GitHub Pages deployment:
- Scrapers run independently (locally or via GitHub Actions) and output JSON to `web/data/`
- The frontend is a pure static SPA that fetches JSON files — no backend server
- GitHub Actions runs scrapers on a cron schedule and deploys `web/` to the `gh-pages` branch

**Scraper framework** (`scrapers/`):
- `base.py`: `BaseScraper` abstract class with unified interface (`scrape()` → `List[JobDict]`, `save_json()`, `generate_stats()`)
- Each platform is a sub-package (e.g., `job51/`, `zhilian/`, `boss/`) inheriting `BaseScraper`
- `runner.py`: CLI entrypoint that orchestrates all scrapers and writes JSON output
- JobDict fields are standardized: `job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, job_url, city, scrape_date, source`

**Frontend** (`web/`):
- Pure HTML/CSS/JS SPA — no build step, no framework
- Platform tabs switch data sources by loading different JSON files
- All search/filter/pagination is client-side against the JSON data
- `app.js` handles data loading and state; `render.js` handles DOM rendering

**Adding a new platform scraper**:
1. Create `scrapers/<platform>/` with a class inheriting `BaseScraper`
2. Register it in `runner.py`'s `get_available_scrapers()`
3. Create a placeholder JSON in `web/data/<platform>.json`
4. Frontend automatically picks up new tabs via `AVAILABLE_SOURCES` in `app.js`

## Key Design Decisions

- No SQLite/database — data lives purely in JSON files for static-site compatibility
- The `job51` scraper uses Playwright to bypass 51job's WAF verification, then `requests` for API calls
- GitHub Actions uses `peaceiris/actions-gh-pages` to deploy `web/` to `gh-pages` branch