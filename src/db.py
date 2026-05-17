"""
SQLite 数据库模块 - 存/读 51job 招聘数据
使用上下文管理器管理连接，支持连接重试处理锁冲突
"""
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from src.config import DB_PATH

__all__ = ['init_db', 'insert_many', 'get_jobs', 'get_stats', 'migrate_from_json']

SCHEMA = '''
CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    job_name     TEXT NOT NULL,
    company_name TEXT DEFAULT '',
    salary       TEXT DEFAULT '',
    work_area    TEXT DEFAULT '',
    work_year    TEXT DEFAULT '',
    education    TEXT DEFAULT '',
    publish_date TEXT DEFAULT '',
    publish_time TEXT DEFAULT '',
    issue_date   TEXT DEFAULT '',
    confirm_date TEXT DEFAULT '',
    update_time  TEXT DEFAULT '',
    job_url      TEXT DEFAULT '',
    city         TEXT DEFAULT '',
    scrape_date  TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city);
CREATE INDEX IF NOT EXISTS idx_jobs_issue_date ON jobs(issue_date DESC);
'''


@contextmanager
def get_conn():
    """上下文管理器：获取数据库连接，退出时自动关闭"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute_with_retry(callback, max_retries=3):
    """带重试的数据库操作（处理 database is locked）"""
    for attempt in range(max_retries):
        try:
            return callback()
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < max_retries - 1:
                wait = 0.5 * (2 ** attempt)
                time.sleep(wait)
                continue
            raise


def init_db():
    """初始化数据库表结构"""
    def _init():
        with get_conn() as conn:
            conn.executescript(SCHEMA)
    _execute_with_retry(_init)


def insert_many(jobs: List[Dict[str, Any]]):
    """批量插入/替换职位数据"""
    def _insert():
        with get_conn() as conn:
            rows = [(
                j.get('job_id', ''), j.get('job_name', ''),
                j.get('company_name', ''), j.get('salary', ''),
                j.get('work_area', ''), j.get('work_year', ''),
                j.get('education', ''), j.get('publish_date', ''),
                j.get('publish_time', ''), j.get('issue_date', ''),
                j.get('confirm_date', ''), j.get('update_time', ''),
                j.get('job_url', ''), j.get('city', ''),
                j.get('scrape_date', ''),
            ) for j in jobs]
            conn.executemany('''
                INSERT OR REPLACE INTO jobs
                (job_id, job_name, company_name, salary, work_area, work_year,
                 education, publish_date, publish_time, issue_date, confirm_date,
                 update_time, job_url, city, scrape_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', rows)
    _execute_with_retry(_insert)


def get_jobs(city: str = '', keyword: str = '',
             page: int = 1, per_page: int = 50) -> Tuple[List[Dict], int]:
    """查询职位数据，返回 (data, total)"""
    def _query():
        with get_conn() as conn:
            conditions = []
            params = []

            if city:
                conditions.append('city = ?')
                params.append(city)
            if keyword:
                kw = f'%{keyword}%'
                conditions.append('(job_name LIKE ? OR company_name LIKE ?)')
                params.extend([kw, kw])

            where = ' AND '.join(conditions) if conditions else '1=1'
            total = conn.execute(
                f'SELECT COUNT(*) FROM jobs WHERE {where}', params
            ).fetchone()[0]

            offset = (page - 1) * per_page
            rows = conn.execute(
                f'SELECT * FROM jobs WHERE {where} ORDER BY issue_date DESC LIMIT ? OFFSET ?',
                params + [per_page, offset]
            ).fetchall()

            # 使用 row.keys() 获取列名（row_factory = sqlite3.Row）
            data = [dict(r) for r in rows]
            return data, total
    return _execute_with_retry(_query)


def get_stats() -> Dict[str, Any]:
    """获取统计数据"""
    def _stats():
        with get_conn() as conn:
            total = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
            companies = conn.execute(
                'SELECT COUNT(DISTINCT company_name) FROM jobs WHERE company_name != ""'
            ).fetchone()[0]
            cities = conn.execute(
                'SELECT city, COUNT(*) as cnt FROM jobs GROUP BY city'
            ).fetchall()
            by_city = {r['city']: r['cnt'] for r in cities}
            return {
                'total_jobs': total,
                'unique_companies': companies,
                'by_city': by_city,
                'cities': list(by_city.keys()),
            }
    return _execute_with_retry(_stats)


def migrate_from_json(json_path: str):
    """从 JSON 文件迁移数据到 SQLite"""
    with open(json_path, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    insert_many(jobs)
    print(f'Migrated {len(jobs)} jobs to SQLite')


if __name__ == '__main__':
    init_db()
    print(f'DB ready: {DB_PATH}')
