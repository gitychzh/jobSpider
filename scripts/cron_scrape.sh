#!/bin/bash
# 51job 每日爬取脚本 - 北京时间上午10点运行
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

LOG="$PROJECT_DIR/data/cron.log"
echo "$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S CST') 开始爬取..." >> "$LOG"

"$PROJECT_DIR/venv/bin/python3" -u src/scraper.py >> "$LOG" 2>&1

echo "$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S CST') 爬取完成" >> "$LOG"
