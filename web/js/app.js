/**
 * app.js — 主逻辑：数据加载、搜索、筛选、分页、平台切换
 *
 * 功能：
 *  - 数据新鲜度指示器
 *  - 实时搜索（debounce）
 *  - 刷新按钮
 *  - 信息栏提示
 *  - 学历筛选（及以上逻辑）
 *  - 薪资范围筛选
 *  - 搜索关键词高亮
 *  - 深色模式切换
 *  - 回到顶部按钮
 *  - 清空筛选
 */
const PER_PAGE = 50;
const AVAILABLE_SOURCES = ['job51', 'zhilian', 'boss'];

// 学历等级映射（用于"及以上"筛选）
const EDU_LEVELS = {
    '初中': 1, '初中及以下': 1,
    '高中': 2,
    '中专': 3, '中技': 3, '中专/中技': 3,
    '大专': 4,
    '本科': 5,
    '硕士': 6,
    '博士': 7,
};

let currentSource = 'job51';
let currentPage = 1;
let currentKeyword = '';
let currentCity = '';
let currentEducation = '';
let currentSalaryRange = '';
let allJobsCache = {};

// ─── 平台切换 ────────────────────────────
function switchSource(source) {
    currentSource = source;
    currentPage = 1;
    currentKeyword = '';
    currentCity = '';
    currentEducation = '';
    currentSalaryRange = '';

    document.getElementById('searchBox').value = '';
    document.getElementById('cityFilter').value = '';
    document.getElementById('educationFilter').value = '';
    document.getElementById('salaryFilter').value = '';

    // 更新tab样式
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.source === source);
    });

    // 加载数据或显示coming-soon
    const cfg = SOURCE_CONFIG[source];
    if (cfg && cfg.available) {
        loadJobs(1);
    } else {
        renderComingSoon(source);
    }
}

// ─── 城市下拉 ────────────────────────────
function updateCityFilter(source) {
    const sel = document.getElementById('cityFilter');
    sel.innerHTML = '<option value="">全部城市</option>';
    const data = allJobsCache[source];
    if (!data || !data.jobs) return;

    const cities = {};
    data.jobs.forEach(j => { if (j.city) cities[j.city] = (cities[j.city] || 0) + 1; });
    Object.entries(cities).sort((a, b) => b[1] - a[1]).forEach(([c, n]) => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = `${c} (${n})`;
        sel.appendChild(opt);
    });
}

// ─── 数据新鲜度 ────────────────────────────
function updateFreshIndicator(lastUpdateStr) {
    const indicator = document.getElementById('freshIndicator');
    if (!lastUpdateStr) {
        indicator.textContent = '';
        indicator.className = 'fresh-indicator';
        return;
    }

    const lastUpdate = new Date(lastUpdateStr + 'Z'); // UTC
    const now = new Date();
    const diffMs = now - lastUpdate;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffMin < 30) {
        indicator.textContent = '🟢 新鲜';
        indicator.className = 'fresh-indicator fresh';
    } else if (diffHour < 3) {
        indicator.textContent = `🟡 ${diffHour}小时前`;
        indicator.className = 'fresh-indicator stale';
    } else if (diffDay < 1) {
        indicator.textContent = `🟡 ${diffHour}小时前`;
        indicator.className = 'fresh-indicator stale';
    } else {
        indicator.textContent = `🔴 ${diffDay}天前`;
        indicator.className = 'fresh-indicator old';
    }
}

// ─── 信息栏 ────────────────────────────
function showInfo(message) {
    const bar = document.getElementById('infoBar');
    bar.textContent = message;
    bar.className = 'info-bar visible';
    setTimeout(() => { bar.className = 'info-bar'; }, 3000);
}

// ─── 数据加载 ────────────────────────────
async function loadSourceData(source) {
    if (allJobsCache[source]) return allJobsCache[source];
    renderLoading();

    try {
        const res = await fetch(`data/${source}.json`);
        if (!res.ok) {
            allJobsCache[source] = { available: false };
            return allJobsCache[source];
        }
        const data = await res.json();
        data.available = true;
        allJobsCache[source] = data;
        return data;
    } catch (e) {
        allJobsCache[source] = { available: false };
        return allJobsCache[source];
    }
}

async function loadStats() {
    try {
        const res = await fetch('data/stats.json');
        if (!res.ok) return;
        const stats = await res.json();

        // 取当前平台的统计
        const scraperStats = stats.scrapers && stats.scrapers[currentSource];
        if (scraperStats) {
            renderStats({
                total_jobs: scraperStats.total_jobs || 0,
                unique_companies: scraperStats.unique_companies || 0,
                by_city: scraperStats.by_city || {},
                by_education: scraperStats.by_education || {},
                salary_summary: scraperStats.salary_summary || {},
                last_update: stats.last_update || '',
            });
            renderStatsPanel(scraperStats);
            updateFreshIndicator(stats.last_update);
        } else {
            renderStats({ total_jobs: 0, unique_companies: 0, by_city: {}, by_education: {}, salary_summary: {}, last_update: stats.last_update || '' });
            updateFreshIndicator(stats.last_update);
        }
    } catch (e) {
        // 忽略
    }
}

async function loadJobs(page) {
    currentPage = page;
    currentCity = document.getElementById('cityFilter').value;
    currentKeyword = document.getElementById('searchBox').value.trim();
    currentEducation = document.getElementById('educationFilter').value;
    currentSalaryRange = document.getElementById('salaryFilter').value;

    renderLoading();

    const data = await loadSourceData(currentSource);
    if (!data.available || !data.jobs) {
        renderComingSoon(currentSource);
        return;
    }

    // 纯前端筛选
    let filtered = data.jobs;

    // 城市筛选
    if (currentCity) {
        filtered = filtered.filter(j => j.city === currentCity);
    }

    // 学历筛选（及以上逻辑）
    if (currentEducation) {
        const minLevel = EDU_LEVELS[currentEducation.replace('及以上', '')] || EDU_LEVELS[currentEducation] || 0;
        filtered = filtered.filter(j => {
            const edu = (j.education || '').trim();
            const level = EDU_LEVELS[edu] || 0;
            // "及以上"意味着：如果筛选条件含"及以上"，则匹配 >= minLevel
            // 如果不含"及以上"（如博士、中专/中技），则精确匹配或模糊匹配
            if (currentEducation.includes('及以上')) {
                return level >= minLevel;
            }
            // 精确筛选：模糊匹配
            return edu.includes(currentEducation.replace('及以上', '')) || edu === currentEducation;
        });
    }

    // 薪资范围筛选
    if (currentSalaryRange) {
        filtered = filtered.filter(j => {
            const salary = j.salary || '';
            if (currentSalaryRange === 'negotiable') {
                return salary === '薪资面议' || !salary;
            }
            // 解析薪资范围（格式如 "8-10千/月" 或 "1-1.5万/月"）
            const monthly = parseSalaryMonthly(salary);
            if (monthly === null) return false;
            const [minK, maxK] = parseSalaryFilter(currentSalaryRange);
            if (maxK === null) return monthly >= minK; // e.g. "50k+"
            return monthly >= minK && monthly <= maxK;
        });
    }

    // 关键词搜索
    if (currentKeyword) {
        const kw = currentKeyword.toLowerCase();
        filtered = filtered.filter(j =>
            (j.job_name && j.job_name.toLowerCase().includes(kw)) ||
            (j.company_name && j.company_name.toLowerCase().includes(kw)) ||
            (j.work_area && j.work_area.toLowerCase().includes(kw))
        );
    }

    // 排序
    const sortField = document.getElementById('sortField').value || 'issue_date';
    const sortOrder = document.getElementById('sortOrder').value || 'desc';
    filtered.sort((a, b) => {
        const va = (a[sortField] || '');
        const vb = (b[sortField] || '');
        const cmp = va.localeCompare(vb);
        return sortOrder === 'desc' ? -cmp : cmp;
    });

    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
    const start = (page - 1) * PER_PAGE;
    const pageData = filtered.slice(start, start + PER_PAGE);

    // 更新信息栏
    let infoParts = [];
    if (currentKeyword) infoParts.push(`搜索「${currentKeyword}」`);
    if (currentCity) infoParts.push(currentCity);
    if (currentEducation) infoParts.push(currentEducation);
    if (currentSalaryRange) infoParts.push(salaryFilterLabel(currentSalaryRange));
    if (infoParts.length > 0) {
        showInfo(`${infoParts.join(' · ')} → ${total} 条`);
    }

    renderJobList(pageData, currentKeyword);
    renderPagination(page, totalPages);
    updateCityFilter(currentSource);
    loadStats();
}

// ─── 统计面板展开/折叠 ────────────────────────────
let statsPanelVisible = false;
function toggleStatsPanel() {
    statsPanelVisible = !statsPanelVisible;
    const panel = document.getElementById('statsPanel');
    const toggle = document.getElementById('statsToggle');
    if (statsPanelVisible) {
        panel.classList.add('visible');
        toggle.textContent = '▲ 收起统计';
    } else {
        panel.classList.remove('visible');
        toggle.textContent = '▼ 查看详细统计';
    }
}

function loadPage(page) {
    loadJobs(page);
}

function filterJobs() {
    loadJobs(1);
}

// ─── 薪资解析辅助 ────────────────────────────
function parseSalaryMonthly(salaryStr) {
    if (!salaryStr || salaryStr === '薪资面议') return null;
    // Match patterns like "8-10千/月", "1-1.5万/月", "10-20千/月", "150-200元/天"
    const match = salaryStr.match(/([\d.]+)-([\d.]+)(千|万)\/月/);
    if (!match) {
        // Try per-day: "150-200元/天" → assume 22 work days
        const dayMatch = salaryStr.match(/([\d.]+)-([\d.]+)元\/天/);
        if (dayMatch) {
            const avg = ((parseFloat(dayMatch[1]) + parseFloat(dayMatch[2])) / 2) * 22 / 1000;
            return avg; // in k
        }
        return null;
    }
    const low = parseFloat(match[1]);
    const high = parseFloat(match[2]);
    const unit = match[3]; // 千 or 万
    const avg = (low + high) / 2;
    return unit === '万' ? avg * 10 : avg; // in k (千)
}

function parseSalaryFilter(filterVal) {
    // "0-3k" → [0, 3], "3-5k" → [3, 5], "50k+" → [50, null]
    if (filterVal.endsWith('+')) return [parseFloat(filterVal.replace('k+', '')), null];
    const parts = filterVal.split('-');
    const maxPart = parts[1].replace('k', '');
    return [parseFloat(parts[0]), parseFloat(maxPart)];
}

function salaryFilterLabel(filterVal) {
    const labels = {
        '0-3k': '3k以下', '3-5k': '3-5k', '5-10k': '5-10k',
        '10-20k': '10-20k', '20-50k': '20-50k', '50k+': '50k以上',
        'negotiable': '薪资面议',
    };
    return labels[filterVal] || filterVal;
}

// ─── 深色模式 ────────────────────────────
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? '' : 'dark';
    document.documentElement.setAttribute('data-theme', next || 'light');
    if (!next) document.documentElement.removeAttribute('data-theme');
    localStorage.setItem('theme', next || 'light');
    document.getElementById('themeToggle').textContent = next === 'dark' ? '☀️' : '🌙';
}

function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        const btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = '☀️';
    }
}

// ─── 回到顶部 ────────────────────────────
function initBackToTop() {
    const btn = document.getElementById('backToTop');
    window.addEventListener('scroll', () => {
        btn.classList.toggle('visible', window.scrollY > 300);
    }, { passive: true });
}

// ─── 清空筛选 ────────────────────────────
function clearFilters() {
    document.getElementById('searchBox').value = '';
    document.getElementById('cityFilter').value = '';
    document.getElementById('educationFilter').value = '';
    document.getElementById('salaryFilter').value = '';
    currentKeyword = '';
    currentCity = '';
    currentEducation = '';
    currentSalaryRange = '';
    loadJobs(1);
}

// ─── 刷新数据 ────────────────────────────
async function refreshData() {
    // 清除缓存
    allJobsCache = {};
    showInfo('正在刷新数据...');
    await loadJobs(1);
    showInfo('数据已刷新');
}

// ─── Debounce搜索 ────────────────────────────
let searchTimer = null;
function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        loadJobs(1);
    }, 300);
}

// ─── 初始化 ────────────────────────────
async function init() {
    // 初始化主题和回到顶部
    initTheme();
    initBackToTop();

    // 加载统计数据确定哪些平台可用
    let availableSet = new Set(['job51']);

    try {
        const res = await fetch('data/stats.json');
        if (res.ok) {
            const stats = await res.json();
            if (stats.available_sources) {
                availableSet = new Set(stats.available_sources);
            }
        }
    } catch (e) { /* ignore */ }

    // 更新 SOURCE_CONFIG
    for (const src of AVAILABLE_SOURCES) {
        if (SOURCE_CONFIG[src]) {
            SOURCE_CONFIG[src].available = availableSet.has(src);
        }
    }

    // 设置tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        const src = btn.dataset.source;
        if (src && SOURCE_CONFIG[src] && !SOURCE_CONFIG[src].available) {
            btn.classList.add('disabled');
        }
    });

    // 默认加载51job
    switchSource('job51');

    // 搜索回车触发 + 实时搜索
    const searchBox = document.getElementById('searchBox');
    searchBox.addEventListener('keypress', e => {
        if (e.key === 'Enter') filterJobs();
    });
    searchBox.addEventListener('input', debounceSearch);
}

document.addEventListener('DOMContentLoaded', init);