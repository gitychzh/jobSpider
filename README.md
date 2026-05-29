# jobSpider — 多平台招聘信息聚合

爬取多个招聘平台数据，通过 Cloudflare Pages + Workers + D1 展示。

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
├── web/                # 静态前端（部署到 Cloudflare Pages）
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js, render.js
│   └── data/           # JSON 本地备份
├── worker/             # Cloudflare Worker API
│   ├── api/index.js    # D1 数据读写 API
│   └angler.toml        # Worker 配置
├── .github/workflows/  # GitHub Actions 自动爬取 + 推送D1
```

## 本地开发

```bash
pip install -r requirements.txt
playwright install chromium

# 运行爬虫（本地保存JSON）
python -m scrapers.runner --source job51

# 运行爬虫并推送到D1
python -m scrapers.runner --source job51 --push-d1

# 本地预览前端
cd web && python -m http.server 8081
# 访问 http://localhost:8081
```

## 部署架构

- **Cloudflare Pages** (`jobspider.pages.dev`): 静态前端
- **Cloudflare Worker** (`jobspider-api`): D1 数据读写 API
- **Cloudflare D1**: SQLite 数据库存储职位数据
- **GitHub Actions**: 每日北京时间 10:00 自动爬取，推送到 D1

也可手动触发: GitHub → Actions → Scrape & Push to D1 → Run workflow

## 添加新平台

1. �� `scrapers/` 下创建子目录，继承 `BaseScraper`
2. 实现 `name`、`display_name`、`scrape()` 方法
3. 在 `scrapers/runner.py` 的 `get_available_scrapers()` 中注册
4. 在 `web/js/app.js` 的 `AVAILABLE_SOURCES` 和 `web/index.html` 的 tabs 中添加