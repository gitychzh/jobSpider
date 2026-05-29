# jobSpider — 多平台招聘信息聚合

爬取多个招聘平台数据，通过 GitHub Pages 静态展示。

当前支持: **51job** | 预留: 智联招聘、Boss直聘

## 项目结构

```
jobSpider/
├── scrapers/           # 爬虫框架
│   ├── base.py         # BaseScraper 抽象基类
│   ├── job51/          # 51job 爬虫
│   ├── zhilian/        # 智联招聘（预留）
│   ├── boss/           # Boss直聘（预留）
│   └── runner.py       # 统一调度器
├── web/                # 静态前端（部署到 gh-pages）
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js, render.js
│   └── data/           # JSON 数据文件
├── .github/workflows/  # GitHub Actions 自动爬取+部署
```

## 本地开发

```bash
pip install -r requirements.txt
playwright install chromium

# 运行爬虫
python -m scrapers.runner --source job51

# 本地预览前端
cd web && python -m http.server 8081
# 访问 http://localhost:8081
```

## 自动部署

GitHub Actions 每日北京时间 10:00 自动爬取 51job 数据，将 `web/` 目录部署到 `gh-pages` 分支。

也可手动触发: GitHub → Actions → Scrape & Deploy → Run workflow

## 添加新平台

1. 在 `scrapers/` 下创建子目录，继承 `BaseScraper`
2. 实现 `name`、`display_name`、`scrape()` 方法
3. 在 `scrapers/runner.py` 的 `get_available_scrapers()` 中注册
4. 在 `web/data/` 下创建占位 JSON
5. 前端 tab 自动识别