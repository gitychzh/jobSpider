# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Run 51job scraper: `python3 -m scrapers.runner --source job51`
- Run all scrapers: `python3 -m scrapers.runner`
- Control page count: `python3 -m scrapers.runner --source job51 --pages 10`
- Local preview frontend: `cd web && python3 -m http.server 8081` → visit http://localhost:8081
- Install dependencies: `pip3 install -r requirements.txt && playwright install chromium --with-deps`
- Deploy to Cloudflare Pages: `CLOUDFLARE_API_TOKEN=cfat_... wrangler pages deploy web/ --project-name=jobspider --branch=main`

## Deployment

This project deploys via **Cloudflare Pages** (replaced GitHub Pages):
- URL: https://job.223722.xyz (also https://jobspider.pages.dev)
- Cloudflare account: `fcd03f4fb32acc1f7073a1fd13645fe6`
- Zone: `223722.xyz` (active, Cloudflare-managed DNS)

**Deploying manually**:
```bash
# Run scraper first (optional)
python3 -m scrapers.runner --source job51 --pages 5
# Then deploy
CLOUDFLARE_API_TOKEN=<token> wrangler pages deploy web/ --project-name=jobspider --branch=main
```

**GitHub Actions** (`scrape.yml`): runs scraper daily at UTC 02:00 (BJT 10:00) and:
1. Commits updated JSON data to the repo
2. Deploys to Cloudflare Pages via `wrangler` action

Requires `CLOUDFLARE_API_TOKEN` secret set in GitHub repo Settings > Secrets.

**Old gh-pages branch**: no longer used for deployment, but kept for history.

## Architecture

This project uses a **static-site architecture**:
- Scrapers output JSON to `web/data/` (no database)
- Frontend is pure HTML/CSS/JS SPA that fetches JSON — no backend server
- Data flow: scraper → JSON files → git commit → Cloudflare Pages CDN

**Scraper framework** (`scrapers/`):
- `base.py`: `BaseScraper` abstract class. Subclasses must implement `name`, `display_name`, `scrape()` → `List[JobDict]`. Provides `save_json()` and `generate_stats()`.
- `runner.py`: CLI entrypoint, orchestrates all scrapers, writes JSON output to `web/data/`
- Each platform is a sub-package inheriting `BaseScraper`
- JobDict fields: `job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, confirm_date, update_time, job_url, city, scrape_date, source`

**51job scraper** (`scrapers/job51/`):
- Uses Playwright to open one search page (bypass WAF), then calls the API via `page.evaluate(JS_FETCH_API)` inside the browser context
- WAF is Alibaba Cloud — it blocks plain HTTP requests but allows browser-sourced fetch
- **JS decryption is NOT applicable** — the API returns plain JSON; the WAF is network-layer blocking, not encryption
- Strategy: visit search page once → WAF passes → all subsequent API calls via JS fetch in same browser page
- Covers 17 cities: 江苏全省(13) + 上海
- `browser.py`: manages Playwright instance lifecycle with stealth mode and auto-restart on crash
- `config.py`: city codes, API base URL, `ApiParams` dataclass for building query params
- Enhanced: API retry (3 attempts), WAF multi-signal detection, data validation & cleaning

**Boss直聘 & 智联招聘**:
- Both marked as "未开放" — Boss has extremely aggressive anti-bot (warlock fingerprint + browser-check JS), Playwright headless is completely blocked
- Zhilian similarly has WAF challenges
- Skeleton classes exist in `scrapers/boss/` and `scrapers/zhilian/`

**Frontend** (`web/`):
- Pure SPA, no build step, no framework
- File structure: `css/style.css`, `js/app.js`, `js/render.js`, `index.html`, `404.html`
- `app.js`: data loading, city/education/salary filter, sort, pagination, debounce search, refresh button, fresh indicator, dark mode toggle, back-to-top button
- `render.js`: job cards (with search keyword highlighting), stats panel, pagination, source tags, relative time display
- `style.css`: responsive design, CSS variables (light + dark themes via `[data-theme="dark"]`), fresh indicator, info bar, skeleton loading, footer

**Frontend features**:
- **Dark mode**: toggle button in header (🌙/☀️), persists via `localStorage`, auto-detects `prefers-color-scheme`, CSS variables switch via `[data-theme="dark"]`
- **Education filter**: hierarchical "及以上" logic — `本科及以上` shows 本科+硕士+博士 using `EDU_LEVELS` mapping
- **Salary filter**: range-based (3k以下, 3k-5k, 5k-10k, 10k-20k, 20k-50k, 50k以上, 薪资面议), parses 51job salary strings (千/月, 万/月, 元/天)
- **Search highlighting**: matched keywords in job name, company, area shown with `.search-highlight` yellow background
- **Back-to-top button**: floating `↑` button appears after scrolling 300px, smooth scroll to top
- **Stats panel**: expandable with city distribution bar chart, education distribution, salary summary

**Adding a new platform scraper**:
1. Create `scrapers/<platform>/` with class inheriting `BaseScraper`
2. Register in `runner.py`'s `get_available_scrapers()`
3. Create `web/data/<platform>.json` placeholder
4. Add to `AVAILABLE_SOURCES` in `app.js` and `SOURCE_CONFIG` in `render.js`
5. Add a tab button in `index.html`
6. Add platform color variables in `style.css` (`--color-<platform>`) and dark mode source-tag styles

## Key Design Decisions

- No SQLite/database — data lives in JSON files for static-site compatibility
- 51job API bypasses WAF by using Playwright JS fetch (not Python requests) — this is the ONLY working method
- Single browser page for all cities — avoids WAF re-verification per city
- Cloudflare Pages deployment (replaced GitHub Pages) — faster CDN, easier management
- 51job covers 17 cities (江苏13城 + 上海) for comprehensive coverage
- GitHub Actions auto-commits data changes + deploys to Cloudflare Pages
- Education filter uses level-based "及以上" logic instead of simple string matching
- Salary filter parses 51job's Chinese salary format (千/月, 万/月, 元/天) to numeric k-values
- Dark mode implemented with CSS custom properties + `[data-theme="dark"]` selector — no JS theme swapping of individual elements

## Common Issues

- **WAF blocking**: if scraper returns 0 jobs, WAF may have blocked the browser. Re-run; Playwright stealth mode helps but is not guaranteed
- **Boss直聘 blocked**: Boss uses warlock fingerprint + browser-check; Playwright headless completely blocked. Need non-headless browser or different approach
- **Empty cities**: some cities (南京, 盐城) may return empty data — the scraper correctly handles this and skips
- **Cloudflare Pages stale data**: deployment is near-instant, but browser cache may show old data briefly
- **Salary filter edge cases**: salaries in non-standard formats (e.g. "面议", "元/天") are handled: "面议" has its own filter option, "元/天" is converted assuming 22 work days/month
- **Dark mode missing styles**: new CSS properties should use CSS variables (not hardcoded colors) so dark mode works automatically. If a new element has hardcoded colors, add a `[data-theme="dark"]` override