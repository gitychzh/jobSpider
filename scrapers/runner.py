"""
爬虫统一调度器 — CLI入口，运行指定/全部爬虫，输出JSON或推送到D1

用法:
  python -m scrapers.runner                # 运行全部，本地保存JSON
  python -m scrapers.runner --source job51  # 只运行51job
  python -m scrapers.runner --push-d1       # 运行后推送到Cloudflare D1
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

from scrapers.base import DATA_DIR, CF_API_URL

CF_IMPORT_SECRET = os.environ.get('CF_IMPORT_SECRET', 'jobSpider2024secret')


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


def push_stats_to_d1(all_stats, total_jobs):
    """Push combined stats to D1 via API"""
    payload = {
        'action': 'insert_jobs',
        'source': 'stats',
        'jobs': [],
    }
    # We don't push stats as jobs; stats are computed on read from D1
    pass


def run_scrapers(source=None, pages_per_city=5, push_d1=False):
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
    start_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    for name in targets:
        scraper = all_scrapers[name]
        print(f"\n>>> 运行 [{scraper.display_name}] 爬虫 <<<")

        try:
            kwargs = {}
            if name == 'job51':
                kwargs['pages_per_city'] = pages_per_city

            jobs = scraper.scrape(**kwargs)
            if jobs:
                # Always save local JSON backup
                path = scraper.save_json(jobs)
                stats = scraper.generate_stats(jobs)
                all_stats[name] = stats
                total_jobs += len(jobs)
                print(f"  本地保存到 {path}, {len(jobs)} 条")

                # Push to D1 if requested
                if push_d1:
                    success = scraper.save_to_d1(jobs)
                    if success:
                        # Log scrape run
                        try:
                            req = urllib.request.Request(
                                f'{CF_API_URL}/api/import',
                                data=json.dumps({
                                    'action': 'log_scrape_run',
                                    'source': name,
                                    'status': 'success',
                                    'total_jobs': len(jobs),
                                    'started_at': start_time_str,
                                }).encode('utf-8'),
                                headers={
                                    'Content-Type': 'application/json',
                                    'X-Import-Secret': CF_IMPORT_SECRET,
                                },
                                method='POST',
                            )
                            urllib.request.urlopen(req, timeout=10)
                        except Exception:
                            pass
            else:
                print(f"  [{scraper.display_name}] 无数据")
        except NotImplementedError:
            print(f"  [{scraper.display_name}] 暂未实现，跳过")
        except Exception as e:
            print(f"  [{scraper.display_name}] 爬取失败: {e}")
            if push_d1:
                try:
                    req = urllib.request.Request(
                        f'{CF_API_URL}/api/import',
                        data=json.dumps({
                            'action': 'log_scrape_run',
                            'source': name,
                            'status': 'error',
                            'total_jobs': 0,
                            'started_at': start_time_str,
                            'error_msg': str(e),
                        }).encode('utf-8'),
                        headers={
                            'Content-Type': 'application/json',
                            'X-Import-Secret': CF_IMPORT_SECRET,
                        },
                        method='POST',
                    )
                    urllib.request.urlopen(req, timeout=10)
                except Exception:
                    pass

    # Save local stats
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
    parser.add_argument('--push-d1', action='store_true',
                        help='爬取后推送到Cloudflare D1数据库')
    args = parser.parse_args()
    run_scrapers(source=args.source, pages_per_city=args.pages, push_d1=args.push_d1)


if __name__ == '__main__':
    main()