"""
爬虫统一调度器 — CLI入口，运行指定/全部爬虫，输出JSON

用法:
  python -m scrapers.runner                # 运行全部
  python -m scrapers.runner --source job51  # 只运行51job
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from scrapers.base import DATA_DIR


def get_available_scrapers():
    """返回所有可用的爬虫实例"""
    scrapers = {}
    try:
        from scrapers.job51 import Job51Scraper
        scrapers['job51'] = Job51Scraper()
    except ImportError:
        pass
    try:
        from scrapers.zhilian import ZhilianScraper
        scrapers['zhilian'] = ZhilianScraper()
    except ImportError:
        pass
    try:
        from scrapers.boss import BossScraper
        scrapers['boss'] = BossScraper()
    except ImportError:
        pass
    return scrapers


def run_scrapers(source=None, pages_per_city=5):
    """运行爬虫并保存数据"""
    all_scrapers = get_available_scrapers()
    if not all_scrapers:
        print("没有可用的爬虫")
        return

    targets = [source] if source else list(all_scrapers.keys())
    if source and source not in all_scrapers:
        print(f"未知爬虫: {source}, 可用: {list(all_scrapers.keys())}")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    all_stats = {}
    total_jobs = 0
    start = time.time()

    for name in targets:
        scraper = all_scrapers[name]
        print(f"\n>>> 运行 [{scraper.display_name}] 爬虫 <<<")

        try:
            kwargs = {}
            if name == 'job51':
                kwargs['pages_per_city'] = pages_per_city

            jobs = scraper.scrape(**kwargs)
            if jobs:
                path = scraper.save_json(jobs)
                stats = scraper.generate_stats(jobs)
                all_stats[name] = stats
                total_jobs += len(jobs)
                print(f"  保存到 {path}, {len(jobs)} 条")
            else:
                print(f"  [{scraper.display_name}] 无数据")
        except NotImplementedError:
            print(f"  [{scraper.display_name}] 暂未实现，跳过")
        except Exception as e:
            print(f"  [{scraper.display_name}] 爬取失败: {e}")

    # 保存合并统计
    now = datetime.now(timezone.utc)
    combined_stats = {
        'last_update': now.strftime('%Y-%m-%d %H:%M:%S'),
        'total_jobs': total_jobs,
        'scrapers': all_stats,
        'available_sources': list(all_scrapers.keys()),
    }
    stats_path = os.path.join(DATA_DIR, 'stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(combined_stats, f, ensure_ascii=False, indent=2)

    print(f"\n总计 {total_jobs} 条, {time.time() - start:.0f}秒")
    print(f"统计保存到 {stats_path}")


def main():
    parser = argparse.ArgumentParser(description='jobSpider 爬虫调度器')
    parser.add_argument('--source', choices=['job51', 'zhilian', 'boss'],
                        help='指定爬虫（默认运行全部）')
    parser.add_argument('--pages', type=int, default=5,
                        help='每个城市爬取页数（默认5）')
    args = parser.parse_args()
    run_scrapers(source=args.source, pages_per_city=args.pages)


if __name__ == '__main__':
    main()