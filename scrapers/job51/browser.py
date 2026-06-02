"""
Playwright 浏览器管理模块 — 启动/复用浏览器、过WAF、取cookies

优化点：
  - 更多UA随机化
  - stealth配置更全面
  - 浏览器崩溃时自动重启
  - 页面超时更合理
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
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/132.0.0.0 Safari/537.36',
    # Chrome on Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/133.0.0.0 Safari/537.36',
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/134.0.0.0',
]


def ensure_browser() -> Tuple:
    """启动或复用 Playwright 浏览器实例（headless + stealth）

    如果浏览器崩溃则自动重启
    """
    global _playwright_instance, _browser, _browser_context

    # 检查现有浏览器是否还活着
    if _browser:
        try:
            if _browser.is_connected():
                return _browser, _browser_context
        except Exception:
            pass
        # 浏览器崩溃了，清理后重建
        print("  浏览器连接断开，正在重启...")
        _cleanup_browser()

    _playwright_instance = sync_playwright().start()
    _browser = _playwright_instance.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-infobars',
        ],
    )
    _browser_context = _browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={
            'width': 1920 + random.randint(0, 80),
            'height': 1080 + random.randint(0, 40),
        },
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        # 模拟真实浏览器环境
        java_script_enabled=True,
        bypass_csp=True,
        extra_http_headers={
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        },
    )

    # 应用 stealth 模式
    Stealth().apply_stealth_sync(_browser_context)

    print("  浏览器启动完成")
    return _browser, _browser_context


def _cleanup_browser():
    """清理旧的浏览器实例"""
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

        # 多信号等待 WAF 通过
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
    _cleanup_browser()