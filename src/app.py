#!/usr/bin/env python3
"""
51job 多城市招聘信息 Web 应用 (Flask)
从 SQLite 数据库读取数据
"""
import os
import json
import subprocess
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from src.config import (
    CITIES, DATA_DIR, STATS_JSON_PATH, PROJECT_DIR,
)
from src.db import get_jobs, get_stats

# ─── Flask 配置 ───────────────────────────────────
app = Flask(
    __name__,
    static_folder='static',
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
)

# 显式使用 venv 的 python
VENV_PYTHON = os.path.join(PROJECT_DIR, 'venv', 'bin', 'python3')
SCRAPER_SCRIPT = os.path.join(PROJECT_DIR, 'src', 'scraper.py')

app.config.from_mapping(
    VENV_PYTHON=VENV_PYTHON,
    SCRAPER_SCRIPT=SCRAPER_SCRIPT,
    STATS_JSON_PATH=STATS_JSON_PATH,
    MAX_PAGES_PER_CITY=20,
)


@app.route('/')
def index():
    return render_template('index.html', cities=list(CITIES.keys()))


@app.route('/api/jobs')
def api_jobs():
    """从 SQLite 读取职位数据（带参数校验和异常处理）"""
    try:
        city = request.args.get('city', '').strip()
        keyword = request.args.get('keyword', '').strip()

        # 参数校验
        try:
            page = int(request.args.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1

        try:
            per_page = int(request.args.get('per_page', 50))
        except (ValueError, TypeError):
            per_page = 50
        per_page = max(1, min(per_page, 200))  # 限制 1-200

        data, total = get_jobs(city=city, keyword=keyword, page=page, per_page=per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)

        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'data': data,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@app.route('/api/stats')
def api_stats():
    """获取统计数据"""
    try:
        s = get_stats()
        stats_path = app.config['STATS_JSON_PATH']
        if os.path.exists(stats_path):
            with open(stats_path, 'r', encoding='utf-8') as f:
                st = json.load(f)
                s['last_update'] = st.get('last_update', '')
        else:
            s['last_update'] = ''
        return jsonify(s)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape', methods=['POST'])
def scrape_jobs():
    """触发爬取任务（支持 pages_per_city 参数）"""
    try:
        # 读取请求体中的 pages_per_city 参数
        pages_per_city = DEFAULT_PAGES_PER_CITY = 5
        try:
            body = request.get_json(silent=True) or {}
            pages_per_city = int(body.get('pages_per_city', 5))
            pages_per_city = max(1, min(pages_per_city, app.config['MAX_PAGES_PER_CITY']))
        except (ValueError, TypeError):
            pages_per_city = 5

        python_path = app.config['VENV_PYTHON']
        scraper_path = app.config['SCRAPER_SCRIPT']

        p = subprocess.run(
            [python_path, scraper_path],
            capture_output=True, text=True, timeout=600,
            env={**os.environ, 'PAGES_PER_CITY': str(pages_per_city)},
        )

        s = get_stats()
        s['last_update'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        with open(app.config['STATS_JSON_PATH'], 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'total_jobs': s.get('total_jobs', 0),
            'by_city': s.get('by_city', {}),
            'message': f'爬取完成，共 {s.get("total_jobs", 0)} 条',
            'output': p.stdout[-500:],
            'error': p.stderr[-500:],
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@app.route('/api/cities')
def api_cities():
    """返回城市列表"""
    return jsonify(CITIES)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)