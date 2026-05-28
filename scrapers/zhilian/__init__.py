"""智联招聘爬虫 — 预留骨架"""
from scrapers.base import BaseScraper


class ZhilianScraper(BaseScraper):
    """智联招聘爬虫（暂未实现）"""

    @property
    def name(self) -> str:
        return 'zhilian'

    @property
    def display_name(self) -> str:
        return '智联招聘'

    def scrape(self, **kwargs):
        raise NotImplementedError('智联招聘爬虫暂未实现')