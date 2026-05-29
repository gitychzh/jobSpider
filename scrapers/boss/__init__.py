"""Boss直聘爬虫 — 预留骨架"""
from scrapers.base import BaseScraper


class BossScraper(BaseScraper):
    """Boss直聘爬虫（暂未实现）"""

    @property
    def name(self) -> str:
        return 'boss'

    @property
    def display_name(self) -> str:
        return 'Boss直聘'

    def scrape(self, **kwargs):
        raise NotImplementedError('Boss直聘爬虫暂未实现')