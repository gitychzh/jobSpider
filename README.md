# 🦞 51job 招聘信息爬虫

多城市 51job 招聘信息爬虫 + Web 展示

## 功能

- 爬取 51job 职位信息（苏州、昆山、常熟、太仓、宿迁）
- 使用 Playwright 自动过 WAF 验证
- 通过 requests 调 API 获取完整字段
- 数据存储在 SQLite 中，同时导出 JSON/CSV
- Flask Web 应用展示数据和统计
- 支持搜索、筛选、分页
- 每日定时爬取（cron）

## 项目结构

```
job51-scraper/
├── src/
│   ├── __init__.py      # 包定义，统一导出
│   ├── config.py        # 城市/API/路径 统一配置
│   ├── browser.py       # Playwright 管理、WAF 过验证
│   ├── storage.py       # JSON/CSV/SQLite 多格式持久化
│   ├── scraper.py       # 爬虫核心逻辑（API 调用）
│   ├── db.py            # SQLite 数据库 CRUD
│   ├── app.py           # Flask Web 应用
│   └── templates/
│       └── index.html   # 前端页面
├── scripts/
│   └── cron_scrape.sh   # cron 定时脚本
├── data/                # 运行时数据
│   ├── jobs.db          # SQLite 数据库
│   ├── jobs.json        # JSON 导出
│   ├── jobs.csv         # CSV 导出
│   ├── stats.json       # 统计信息
│   └── history/         # 历史备份
├── venv/                # Python 虚拟环境
├── requirements.txt     # 依赖清单
└── .gitignore           # 忽略规则
```

## 安装

```bash
cd job51-scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 使用

**爬取数据：**
```bash
python src/scraper.py
```

**启动 Web 应用：**
```bash
python src/app.py
```
访问 http://localhost:8081

**定时任务：**
crontab 配置（每日 22:00）：
```
0 22 * * * /path/to/job51-scraper/scripts/cron_scrape.sh
```
