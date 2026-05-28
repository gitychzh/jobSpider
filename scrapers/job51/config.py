"""51job 配置 — 城市代码、API参数"""
from dataclasses import dataclass
from typing import Dict

# ─── 城市配置 ───────────────────────────────────
CITIES: Dict[str, str] = {
    "苏州": "070300",
    "昆山": "070600",
    "常熟": "070700",
    "太仓": "071600",
    "宿迁": "072000",
}

# ─── API 参数 ────────────────────────────────────
API_BASE = "https://we.51job.com/api/job/search-pc"


@dataclass
class ApiParams:
    """51job search-pc API 固定参数"""
    api_key: str = "51job"
    search_type: str = "2"
    keyword_type: str = "2"
    issue_date: str = "4"
    sort_type: str = "0"
    page_size: str = "20"
    source: str = "1"
    page_code: str = "sou|sou|soulb"
    scene: str = "7"
    keyword: str = ""
    function: str = ""
    industry: str = ""
    job_area2: str = ""
    landmark: str = ""
    metro: str = ""
    salary: str = ""
    work_year: str = ""
    degree: str = ""
    company_type: str = ""
    company_size: str = ""
    job_type: str = ""
    request_id: str = ""
    account_id: str = ""

    def to_dict(self, job_area: str, page_num: int) -> dict:
        import time
        return {
            'api_key': self.api_key,
            'timestamp': int(time.time() * 1000),
            'keyword': self.keyword,
            'searchType': self.search_type,
            'function': self.function,
            'industry': self.industry,
            'jobArea': job_area,
            'jobArea2': self.job_area2,
            'landmark': self.landmark,
            'metro': self.metro,
            'salary': self.salary,
            'workYear': self.work_year,
            'degree': self.degree,
            'companyType': self.company_type,
            'companySize': self.company_size,
            'jobType': self.job_type,
            'issueDate': self.issue_date,
            'sortType': self.sort_type,
            'pageNum': page_num,
            'requestId': self.request_id,
            'keywordType': self.keyword_type,
            'pageSize': self.page_size,
            'source': self.source,
            'accountId': self.account_id,
            'pageCode': self.page_code,
            'scene': self.scene,
        }


# ─── 爬虫默认参数 ────────────────────────────────
DEFAULT_PAGES_PER_CITY = 5