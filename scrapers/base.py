"""
BaseScraper 抽象基类 — 所有平台爬虫的统一接口

子类必须实现:
  name: 爬虫标识 (如 'job51')
  display_name: 显示名称 (如 '51job')
  scrape() → List[JobDict]

JobDict 统一字段:
  job_id, job_name, company_name, salary, work_area,
  work_year, education, issue_date, job_url, city,
  scrape_date, source
"""
import json
import os
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'web', 'data')

# Cloudflare D1 API endpoint (set via env CF_API_URL or default)
CF_API_URL = os.environ.get(
    'CF_API_URL',
    'https://jobSpider-api.gitychzh.workers.dev'
)
CF_IMPORT_SECRET = os.environ.get('CF_IMPORT_SECRET', 'jobSpider2024secret')


class BaseScraper(ABC):
    """招聘信息爬虫基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """爬虫标识，如 'job51'、'zhilian'、'boss'"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """显示名称，如 '51job'、'智联招聘'、'Boss直聘'"""

    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict]:
        """执行爬取，返回职位列表"""

    def save_json(self, jobs: List[Dict]) -> str:
        """将职位数据保存为JSON文件（本地备份）
        Returns:
            保存路径
        """
        os.makedirs(DATA_DIR, exist_ok=True)
        path = os.path.join(DATA_DIR, f'{self.name}.json')
        now = datetime.now(timezone.utc)
        output = {
            'source': self.name,
            'display_name': self.display_name,
            'last_update': now.strftime('%Y-%m-%d %H:%M:%S'),
            'total': len(jobs),
            'jobs': jobs,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return path

    def save_to_d1(self, jobs: List[Dict]) -> bool:
        """将职位数据保存到 Cloudflare D1 via API"""
        if not jobs:
            return True

        batch_size = 50
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i+batch_size]
            payload = {
                'action': 'insert_jobs',
                'source': self.name,
                'jobs': batch,
            }
            try:
                req = urllib.request.Request(
                    f'{CF_API_URL}/api/import',
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'X-Import-Secret': CF_IMPORT_SECRET,
                    },
                    method='POST',
                )
                resp = urllib.request.urlopen(req, timeout=30)
                result = json.loads(resp.read())
                if not result.get('success'):
                    print(f"  D1 batch {i//batch_size+1} failed: {result.get('error')}")
                    return False
            except Exception as e:
                print(f"  D1 batch {i//batch_size+1} error: {e}")
                return False

        print(f"  D1: {len(jobs)} jobs saved")
        return True

    def generate_stats(self, jobs: List[Dict]) -> Dict:
        """生成统计数据"""
        cities = {}
        companies = set()
        for j in jobs:
            city = j.get('city', '')
            if city:
                cities[city] = cities.get(city, 0) + 1
            c = j.get('company_name', '')
            if c:
                companies.add(c)
        return {
            'source': self.name,
            'display_name': self.display_name,
            'total_jobs': len(jobs),
            'unique_companies': len(companies),
            'by_city': cities,
        }