"""
51job 多城市爬虫 — 核心逻辑
全程使用 Playwright 在浏览器内调 API，绕过阿里云 WAF
策略：只访问一次搜索页过WAF，后续全用 JS fetch API

优化点：
  - 增强WAF等待逻辑（检测多种信号）
  - API调用失败时自动重试（最多3次）
  - 数据去重（全局+城市级别）
  - 请求间随机延迟减少被封风险
  - 更详细的日志输出
  - 数据字段验证与清洗
"""
import time
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
        if (!res.ok) return {error: 'HTTP ' + res.status, status: res.status};
        const text = await res.text();
        if (text.startsWith('<') || text.length < 100) return {error: 'WAF拦截', isHtml: true};
        return JSON.parse(text);
    } catch(e) {
        return {error: e.message};
    }
}
"""

# 每次API调用最大重试次数
MAX_API_RETRIES = 3


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

        # 访问搜索页，通过 WAF — 增强等待逻辑
        page = ctx.new_page()
        first_code = list(CITIES.values())[0]
        search_url = (
            f"https://we.51job.com/pc/search?keyword=&keywordType=2"
            f"&jobArea={first_code}&issuedDate=4&pageNum=1&pageSize=20"
        )

        waf_passed = self._pass_waf(page, search_url)
        if not waf_passed:
            print("  WAF验证失败，退出爬取")
            page.close()
            close_browser()
            return []

        # 爬取各城市
        all_seen: set = set()
        all_jobs: list = []

        for city, code in CITIES.items():
            print(f"\n-- [{city}] code={code} --")
            city_jobs = self._scrape_city_in_browser(
                page, city, code, pages_per_city, all_seen
            )
            all_jobs.extend(city_jobs)
            print(f"  {city}: 本轮{len(city_jobs)}条, 累计{len(all_jobs)}条")

        page.close()
        close_browser()
        elapsed = time.time() - start
        print(f"\n完成! 共 {len(all_jobs)} 条, {elapsed:.0f}秒, "
              f"平均{elapsed/len(all_jobs):.1f}秒/条")
        return all_jobs

    def _pass_waf(self, page, search_url: str) -> bool:
        """增强的WAF验证：多信号检测，更长等待"""
        try:
            print("  访问搜索页，等待WAF验证...")
            page.goto(search_url, timeout=30000, wait_until='domcontentloaded')

            # 多信号检测 WAF 是否通过
            for attempt in range(40):  # 最长等40秒
                try:
                    # 信号1：joblist-item 出现
                    joblist_cnt = page.evaluate(
                        "document.querySelectorAll('.joblist-item').length"
                    )
                    if joblist_cnt >= 1:
                        print(f"  WAF通过 (检测到{joblist_cnt}个职位项, {attempt}秒)")
                        return True

                    # 信号2：页面有 job-search-result
                    result_cnt = page.evaluate(
                        "document.querySelectorAll('.job-search-result').length"
                    )
                    if result_cnt >= 1:
                        print(f"  WAF通过 (搜索结果容器出现, {attempt}秒)")
                        return True

                    # 信号3：检测页面标题是否正常（非WAF拦截页）
                    title = page.evaluate("document.title")
                    if title and '51job' in title.lower() and '验证' not in title:
                        # 页面标题正常，但可能数据还在加载
                        pass

                except Exception:
                    pass
                time.sleep(1)

            # 即使没检测到joblist，如果页面标题正常，也尝试继续
            try:
                title = page.evaluate("document.title")
                if title and '51job' in title.lower():
                    print("  WAF等待超时，但页面标题正常，尝试API调用")
                    return True
            except Exception:
                pass

            print("  WAF验证完全失败")
            return False

        except Exception as e:
            print(f"  搜索页加载失败: {e}")
            return False

    def _call_api_with_retry(self, page, params: dict) -> Optional[dict]:
        """API调用带重试逻辑"""
        for attempt in range(MAX_API_RETRIES):
            try:
                time.sleep(random.uniform(0.5, 1.5))
                data = page.evaluate(JS_FETCH_API, params)

                if isinstance(data, dict) and 'error' in data:
                    err = data['error']
                    if 'WAF' in err or data.get('isHtml'):
                        if attempt < MAX_API_RETRIES - 1:
                            print(f"  WAF拦截(重试{attempt+1}/{MAX_API_RETRIES})")
                            time.sleep(random.uniform(2, 4))
                            continue
                        else:
                            print(f"  WAF拦截(重试耗尽)")
                            return None
                    if 'HTTP' in err:
                        status = data.get('status', 0)
                        if status == 429:  # Rate limit
                            if attempt < MAX_API_RETRIES - 1:
                                print(f"  429限流(重试{attempt+1}/{MAX_API_RETRIES})")
                                time.sleep(random.uniform(5, 10))
                                continue
                            else:
                                print(f"  429限流(重试耗尽)")
                                return None
                        print(f"  HTTP错误{status}, 停止")
                        return None
                    # 其他错误
                    if attempt < MAX_API_RETRIES - 1:
                        print(f"  错误:{err}(重试{attempt+1}/{MAX_API_RETRIES})")
                        time.sleep(random.uniform(1, 3))
                        continue
                    return None

                # 成功获取数据
                return data

            except Exception as e:
                if attempt < MAX_API_RETRIES - 1:
                    print(f"  evaluate异常:{e}(重试{attempt+1}/{MAX_API_RETRIES})")
                    time.sleep(random.uniform(2, 5))
                    continue
                print(f"  evaluate异常:{e}(重试耗尽)")
                return None

        return None

    def _scrape_city_in_browser(self, page, city, code, pages, all_seen):
        """在同一页面内逐页调 API — 增强版"""
        jobs, seen = [], set()
        api_params = ApiParams()

        for pg in range(1, pages + 1):
            print(f"  第{pg}/{pages}页 ", end="", flush=True)
            params = api_params.to_dict(job_area=code, page_num=pg)

            data = self._call_api_with_retry(page, params)
            if data is None:
                print("API调用失败, 跳过剩余页")
                break

            # 解析数据
            try:
                job_list = data.get('resultbody', {}).get('job', {}).get('items', [])
            except (AttributeError, TypeError):
                print("数据结构异常, 跳过")
                break

            if not job_list:
                print("空数据, 该城市可能无更多职位")
                break

            now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            added = 0
            skipped = 0

            for j in job_list:
                jid = str(j.get('jobId', ''))
                title = (j.get('jobName') or '').strip()
                if not jid or not title:
                    skipped += 1
                    continue
                if jid in all_seen or jid in seen:
                    skipped += 1
                    continue
                seen.add(jid)
                all_seen.add(jid)

                # 数据清洗
                job_item = {
                    'job_id': jid,
                    'job_name': title,
                    'company_name': _clean_str(j.get('companyName')),
                    'salary': _clean_str(j.get('provideSalaryString')),
                    'work_area': _clean_str(j.get('jobAreaString')),
                    'work_year': _clean_str(j.get('workYearString')),
                    'education': _clean_str(j.get('degreeString')),
                    'issue_date': _clean_str(j.get('issueDateString')),
                    'confirm_date': _clean_str(j.get('confirmDateString')),
                    'update_time': _clean_str(j.get('updateDateTime')),
                    'job_url': _clean_url(j.get('jobHref')),
                    'city': city,
                    'scrape_date': now,
                    'source': self.name,
                }

                # 基本数据验证：至少有公司名或工作区域
                if not job_item['company_name'] and not job_item['work_area']:
                    skipped += 1
                    continue

                jobs.append(job_item)
                added += 1

            print(f"+{added}条(skip:{skipped})")

            # 如果这页没有新增有效数据，说明已经到底了
            if added == 0:
                print("  无新增数据, 停止翻页")
                break

        return jobs


def _clean_str(val) -> str:
    """清洗字符串字段"""
    if val is None:
        return ''
    return str(val).strip()


def _clean_url(url) -> str:
    """清洗URL字段，确保是有效链接"""
    if not url:
        return ''
    url = str(url).strip()
    if not url.startswith('http'):
        return ''
    return url