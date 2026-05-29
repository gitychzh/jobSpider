"""
51job 多城市爬虫 — 核心逻辑
全程使用 Playwright 在浏览器内调 API，绕过阿里云 WAF
策略：只访问一次搜索页过WAF，后续全用 JS fetch  API
"""
import time
import random
from datetime import datetime, timezone
from typing import Dict, List

from scrapers.base import BaseScraper
from scrapers.job51.config import CITIES, ApiParams, DEFAULT_PAGES_PER_CITY
from scrapers.job51.browser import ensure_browser, close_browser

JS_FETCH_API = """
async (params) => {
    const url = 'https://we.51job.com/api/job/search-pc?' + new URLSearchParams(params).toString();
    try {
        const res = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: {'Accept': 'application/json, text/plain, */*'}
        });
        if (!res.ok) return {error: 'HTTP ' + res.status};
        const text = await res.text();
        if (text.startsWith('<') || text.length < 100) return {error: 'WAF拦截'};
        return JSON.parse(text);
    } catch(e) {
        return {error: e.message};
    }
}
"""


class Job51Scraper(BaseScraper):

    @property
    def name(self) -> str:
        return 'job51'

    @property
    def display_name(self) -> str:
        return '51job'

    def scrape(self, pages_per_city: int = DEFAULT_PAGES_PER_CITY) -> List[Dict]:
        """爬取所有城市数据"""
        start = time.time()
        now_utc = datetime.now(timezone.utc)
        print(f"\n{'='*55}")
        print(f"51job 多城市爬虫 {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   {list(CITIES.keys())} | 各{pages_per_city}页 | 近1个月")
        print(f"{'='*55}")

        browser, ctx = ensure_browser()
        if not browser or not browser.is_connected():
            print("浏览器启动失败")
            return []

        # 只访问一次搜索页，通过 WAF
        page = ctx.new_page()
        first_code = list(CITIES.values())[0]
        search_url = (
            f"https://we.51job.com/pc/search?keyword=&keywordType=2"
            f"&jobArea={first_code}&issuedDate=4&pageNum=1&pageSize=20"
        )
        try:
            page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
            # 等WAF验证完成：页面有joblist或等待足够久
            waf_ok = False
            for _ in range(30):
                try:
                    cnt = page.evaluate("document.querySelectorAll('.joblist-item').length")
                    if cnt >= 1:
                        waf_ok = True
                        break
                except Exception:
                    pass
                time.sleep(1)
            if not waf_ok:
                # 即使没检测到joblist，也等够了，可能页面结构变了
                print("  WAF等待超时，继续尝试API调用")
            else:
                print("  WAF验证通过")
        except Exception as e:
            print(f"  搜索页加载失败: {e}")
            page.close()
            close_browser()
            return []

        all_seen: set = set()
        all_jobs: list = []

        for city, code in CITIES.items():
            print(f"\n-- [{city}] code={code} --")
            city_jobs = self._scrape_city_in_browser(page, city, code, pages_per_city, all_seen)
            all_jobs.extend(city_jobs)
            print(f"  {city}: {len(city_jobs)} 条")

        page.close()
        close_browser()
        print(f"\n完成! 共 {len(all_jobs)} 条, {time.time() - start:.0f}秒")
        return all_jobs

    def _scrape_city_in_browser(self, page, city, code, pages, all_seen):
        """在同一页面内逐页调 API"""
        jobs, seen = [], set()
        api_params = ApiParams()

        for pg in range(1, pages + 1):
            print(f"  第{pg}/{pages}页 ", end="", flush=True)
            params = api_params.to_dict(job_area=code, page_num=pg)

            try:
                time.sleep(random.uniform(0.5, 1.5))
                data = page.evaluate(JS_FETCH_API, params)

                if isinstance(data, dict) and 'error' in data:
                    err = data['error']
                    if 'WAF' in err:
                        print(f"WAF拦截，跳过剩余页")
                        break
                    print(f"错误: {err}, 跳过剩余页")
                    break

                job_list = data.get('resultbody', {}).get('job', {}).get('items', [])
            except Exception as e:
                print(f"错误: {e}")
                break

            if not job_list:
                print(f"空数据")
                break

            now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            added = 0
            for j in job_list:
                jid = str(j.get('jobId', ''))
                title = (j.get('jobName') or '').strip()
                if not jid or not title:
                    continue
                if jid in all_seen or jid in seen:
                    continue
                seen.add(jid)
                all_seen.add(jid)

                jobs.append({
                    'job_id': jid,
                    'job_name': title,
                    'company_name': (j.get('companyName') or '').strip(),
                    'salary': (j.get('provideSalaryString') or '').strip(),
                    'work_area': (j.get('jobAreaString') or '').strip(),
                    'work_year': (j.get('workYearString') or '').strip(),
                    'education': (j.get('degreeString') or '').strip(),
                    'issue_date': (j.get('issueDateString') or '').strip(),
                    'confirm_date': (j.get('confirmDateString') or '').strip(),
                    'update_time': (j.get('updateDateTime') or '').strip(),
                    'job_url': j.get('jobHref') or '',
                    'city': city,
                    'scrape_date': now,
                    'source': self.name,
                })
                added += 1

            print(f"+{added}条")
            if added == 0:
                break

        return jobs