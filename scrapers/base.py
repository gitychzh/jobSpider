"""
BaseScraper 抽象基类 — 所有平台爬虫的统一接口

子类必须实现:
  name: 爬虫标识 (如 'job51')
  display_name: 显示名称 (如 '51job')
  scrape() → List[JobDict]

JobDict 统一字段:
  job_id, job_name, company_name, salary, work_area,
  work_year, education, issue_date, confirm_date, update_time,
  job_url, city, scrape_date, source
"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'web', 'data')


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
        """将职位数据保存为JSON文件

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

    def generate_stats(self, jobs: List[Dict]) -> Dict:
        """生成统计数据"""
        cities = {}
        companies = set()
        salary_ranges = {}
        educations = {}

        for j in jobs:
            city = j.get('city', '')
            if city:
                cities[city] = cities.get(city, 0) + 1
            c = j.get('company_name', '')
            if c:
                companies.add(c)

            # 统计学历分布
            edu = j.get('education', '')
            if edu:
                educations[edu] = educations.get(edu, 0) + 1

            # 统计薪资范围（简单分类）
            salary = j.get('salary', '')
            if salary and salary != '薪资面议':
                salary_ranges[salary] = salary_ranges.get(salary, 0) + 1
            else:
                salary_ranges['薪资面议'] = salary_ranges.get('薪资面议', 0) + 1

        return {
            'source': self.name,
            'display_name': self.display_name,
            'total_jobs': len(jobs),
            'unique_companies': len(companies),
            'by_city': cities,
            'by_education': educations,
            'salary_summary': {
                '面议': salary_ranges.get('薪资面议', 0),
                '有明确薪资': sum(v for k, v in salary_ranges.items() if k != '薪资面议'),
            },
        }