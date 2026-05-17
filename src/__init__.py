"""job51-scraper: 51job 多城市招聘信息爬虫

模块结构：
  config.py   — 城市列表、API参数、路径配置
  browser.py  — Playwright 浏览器管理、WAF验证
  storage.py  — JSON/CSV/SQLite 多格式持久化
  db.py       — SQLite 数据库 CRUD
  scraper.py  — 爬虫核心逻辑
  app.py      — Flask Web 展示
"""
from src.scraper import scrape_all, scrape_city
from src.browser import get_cookies, close_browser
from src.storage import save_jobs
from src.db import init_db, insert_many, get_jobs, get_stats
from src.config import CITIES, DATA_DIR, DEFAULT_PAGES_PER_CITY