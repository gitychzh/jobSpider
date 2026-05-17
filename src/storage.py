"""
数据存储模块 — JSON/CSV/SQLite 多格式持久化
操作均创建数据副本，不修改原始 dict（符合不可变性原则）
"""
import csv
import json
import os
import copy
from datetime import datetime, timezone
from typing import Dict, List

from src.config import (
    DATA_DIR, HISTORY_DIR, JOBS_JSON_PATH, JOBS_CSV_PATH, STATS_JSON_PATH,
)
from src.db import init_db, insert_many

__all__ = ['save_jobs']


def save_jobs(jobs: List[Dict], city_stats: Dict[str, int]):
    """保存职位数据到 JSON / CSV / SQLite / 统计 / 历史备份

    Args:
        jobs: 职位列表（原始数据，不会被修改）
        city_stats: 各城市数量统计 {'苏州': 95, ...}
    """
    if not jobs:
        print("  ⚠️ 无数据可保存")
        return

    now = datetime.now(timezone.utc)
    ts = now.strftime('%Y%m%d_%H%M%S')
    os.makedirs(HISTORY_DIR, exist_ok=True)

    # ── JSON（原数据不动） ────────────────────────
    with open(JOBS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    # ── CSV（创建副本，补映射字段） ────────────────
    csv_jobs = copy.deepcopy(jobs)
    for j in csv_jobs:
        j['publish_date'] = j.get('issue_date', '')[:10] if j.get('issue_date') else ''
        j['publish_time'] = j.get('confirm_date', '') if j.get('confirm_date') else ''
    with open(JOBS_CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=csv_jobs[0].keys())
        w.writeheader()
        w.writerows(csv_jobs)

    # ── 历史备份 ──────────────────────────────────
    history_path = os.path.join(HISTORY_DIR, f'jobs_{ts}.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    # ── 统计 ──────────────────────────────────────
    with open(STATS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'last_update': now.strftime('%Y-%m-%d %H:%M:%S'),
            'total_jobs': len(jobs),
            'by_city': city_stats,
            'status': 'SUCCESS',
        }, f, ensure_ascii=False, indent=2)

    # ── SQLite（创建副本，补映射字段）───────────────
    try:
        db_jobs = copy.deepcopy(jobs)
        for j in db_jobs:
            j['publish_date'] = j.get('issue_date', '')[:10] if j.get('issue_date') else ''
            j['publish_time'] = j.get('confirm_date', '') if j.get('confirm_date') else ''
        init_db()
        insert_many(db_jobs)
        print(f"  💾 SQLite({len(jobs)}条) ✅")
    except Exception as e:
        print(f"  ⚠️ SQLite 写入失败: {e}")

    print(f"  💾 JSON({len(jobs)}条) | {city_stats} | 历史备份: {ts}")