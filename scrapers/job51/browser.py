"""
Playwright 浏览器管理模块 — 启动/复用浏览器、过WAF、取cookies
复用浏览器实例减少资源消耗，WAF失败时支持指定城市重试
"""
import time
import random
from typing import Optional, Dict, Tuple

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from scrapers.job51.config import CITIES

__all__ = ['ensure_browser', 'get_cookies', 'close_browser']

_playwright_instance = None
_browser = None
_browser_context = None

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0 Safari/537.36',
]


def ensure_browser() -> Tuple:
    """启动或复用 Playwright 浏览器实例（headless + stealth）"""
    global _playwright_instance, _browser, _browser_context
    if _browser and _browser.is_connected():
        return _browser, _browser_context

    _playwright_instance = sync_playwright().start()
    _browser = _playwright_instance.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    _browser_context = _browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={
            'width': 1920 + random.randint(0, 80),
            'height': 1080 + random.randint(0, 40),
        },
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
    )
    Stealth().apply_stealth_sync(_browser_context)
    return _browser, _browser_context


def get_cookies(city_code: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Playwright 打开搜索页 → 等 WAF 通过 → 取 cookies"""
    try:
        browser, ctx = ensure_browser()
        page = ctx.new_page()

        code = city_code or list(CITIES.values())[0]
        url = (
            f"https://we.51job.com/pc/search?keyword=&keywordType=2"
            f"&jobArea={code}&issuedDate=4&pageNum=1&pageSize=20"
        )
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(3)

        for _ in range(15):
            cnt = page.evaluate("document.querySelectorAll('.joblist-item').length")
            if cnt >= 5:
                break
            time.sleep(1)

        cookie_list = ctx.cookies()
        page.close()
        return {c['name']: c['value'] for c in cookie_list} if cookie_list else None

    except Exception as e:
        print(f"  Playwright WAF 验证失败: {e}")
        return None


def close_browser():
    """关闭浏览器实例"""
    global _playwright_instance, _browser, _browser_context
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
    if _playwright_instance:
        try:
            _playwright_instance.stop()
        except Exception:
            pass
    _browser = None
    _browser_context = None
    _playwright_instance = None