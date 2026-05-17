"""
51job 多城市爬虫 — 核心逻辑
Playwright 过 WAF → requests 调 API → 5城爬取 → 存储

模块分工：
  browser.py  — 浏览器管理、WAF验证、cookie获取
  storage.py  — JSON/CSV/SQLite 多格式持久化
  config.py   — 城市列表、API参数、路径配置
  db.py       — SQLite 数据库操作
"""
import time
import random
import requests
from datetime import datetime, timezone

from src.config import CITIES, API_BASE, ApiParams, DEFAULT_PAGES_PER_CITY
from src.browser import get_cookies, close_browser
from src.storage import save_jobs

__all__ = ['scrape_all', 'scrape_city']


def scrape_all(pages_per_city: int = DEFAULT_PAGES_PER_CITY):
    """主入口：爬取所有城市数据

    Args:
        pages_per_city: 每个城市爬取页数（默认5，每页20条）
    """
    start = time.time()
    now_utc = datetime.now(timezone.utc)
    print(f"\n{'='*55}")
    print(f"🦞 51job 多城市爬虫 {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   {list(CITIES.keys())} | 各{pages_per_city}页 | 近1个月")
    print(f"{'='*55}")

    # 1. Playwright 过 WAF 获取初始 cookies
    cookies = get_cookies()
    if not cookies:
        print("❌ WAF 验证失败，无法获取 cookies")
        close_browser()
        return

    # 2. 全局去重
    all_seen: set = set()
    all_jobs: list = []
    city_stats: dict = {}

    # 3. 逐城市爬取
    for city, code in CITIES.items():
        print(f"\n── [{city}] code={code} ──")
        city_jobs = scrape_city(cookies, city, code, pages_per_city, all_seen)
        city_stats[city] = len(city_jobs)
        all_jobs.extend(city_jobs)
        print(f"  {city}: {len(city_jobs)} 条")
        time.sleep(random.uniform(1, 3))

    # 4. 关闭浏览器
    close_browser()

    # 5. 保存数据
    save_jobs(all_jobs, city_stats)
    print(f"\n✅ 完成! 共 {len(all_jobs)} 条, {time.time() - start:.0f}秒")
    return all_jobs


def scrape_city(cookies, city, code, pages, all_seen):
    """用 requests 调 API 爬一个城市的多页数据。

    每页独立请求，WAF 拦截时用当前城市重新过验证。
    """
    jobs, seen = [], set()
    api_params = ApiParams()

    # 构建持久 Session（带 cookies）
    s = requests.Session()
    for name, value in cookies.items():
        s.cookies.set(name, value, domain='.51job.com', path='/')
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://we.51job.com/pc/search',
        'Origin': 'https://we.51job.com',
    })

    waf_retried = False  # 每个城市最多重试一次 WAF

    for pg in range(1, pages + 1):
        print(f"  第{pg}/{pages}页 ", end="", flush=True)
        params = api_params.to_dict(job_area=code, page_num=pg)

        try:
            time.sleep(random.uniform(1, 3))
            r = s.get(API_BASE, params=params, timeout=15)

            # 检查 WAF 拦截（返回 HTML 而非 JSON）
            ct = r.headers.get('content-type', '')
            if 'text/html' in ct or len(r.text) < 100:
                if not waf_retried:
                    print(f"⏱️WAF拦截 (用[{city}]重新获取cookie)")
                    new_cookies = get_cookies(city_code=code)
                    if new_cookies:
                        s.cookies.clear()
                        for name, value in new_cookies.items():
                            s.cookies.set(name, value, domain='.51job.com', path='/')
                        r = s.get(API_BASE, params=params, timeout=15)
                        waf_retried = True
                    else:
                        print(f"❌ cookie获取失败，跳过剩余页")
                        break
                else:
                    print(f"❌ WAF二次拦截，跳过剩余页")
                    break

            data = r.json()
            job_list = data.get('resultbody', {}).get('job', {}).get('items', [])
        except Exception as e:
            print(f"❌ {e}")
            break

        if not job_list:
            print(f"空数据")
            break

        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        added = 0
        for j in job_list:
            jid = str(j.get('jobId', ''))
            title = j.get('jobName', '').strip()
            if not jid or not title:
                continue
            if jid in all_seen or jid in seen:
                continue
            seen.add(jid)
            all_seen.add(jid)

            jobs.append({
                'job_id': jid,
                'job_name': title,
                'company_name': j.get('companyName', '').strip(),
                'salary': j.get('provideSalaryString', '').strip(),
                'work_area': j.get('jobAreaString', '').strip(),
                'work_year': j.get('workYearString', '').strip(),
                'education': j.get('degreeString', '').strip(),
                'issue_date': j.get('issueDateString', '').strip(),
                'confirm_date': j.get('confirmDateString', '').strip(),
                'update_time': j.get('updateDateTime', '').strip(),
                'job_url': j.get('jobHref', ''),
                'city': city,
                'scrape_date': now,
            })
            added += 1

        print(f"+{added}条")
        if added == 0:
            break

    return jobs


if __name__ == '__main__':
    scrape_all()