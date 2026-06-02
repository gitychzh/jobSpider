/**
 * app.js — 主逻辑：数据加载、搜索、筛选、分页、平台切换
 *
 * 功能：
 *  - 数据新鲜度指示器
 *  - 实时搜索（debounce）
 *  - 刷新按钮
 *  - 信息栏提示
 *  - 学历筛选
 *  - 清空筛选
 */
const PER_PAGE = 50;
const AVAILABLE_SOURCES = ['job51', 'zhilian', 'boss'];

let currentSource = 'job51';
let currentPage = 1;
let currentKeyword = '';
let currentCity = '';
let currentEducation = '';
let allJobsCache = {};

// ─── 平台切换 ────────────────────────────
function switchSource(source) {
    currentSource = source;
    currentPage = 1;
    currentKeyword = '';
    currentCity = '';
    currentEducation = '';

    document.getElementById('searchBox').value = '';
    document.getElementById('cityFilter').value = '';
    document.getElementById('educationFilter').value = '';

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
                last_update: stats.last_update || '',
            });
            updateFreshIndicator(stats.last_update);
        } else {
            renderStats({ total_jobs: 0, unique_companies: 0, by_city: {}, last_update: stats.last_update || '' });
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

    // 学历筛选（模糊匹配，因为51job的学历格式多样）
    if (currentEducation) {
        filtered = filtered.filter(j => {
            const edu = (j.education || '').toLowerCase();
            const target = currentEducation.toLowerCase();
            return edu.includes(target) || edu === target;
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
    if (currentEducation) infoParts.push(currentEducation + '及以上');
    if (infoParts.length > 0) {
        showInfo(`${infoParts.join(' · ')} → ${total} 条`);
    }

    renderJobList(pageData, currentKeyword);
    renderPagination(page, totalPages);
    updateCityFilter(currentSource);
    loadStats();
}

function loadPage(page) {
    loadJobs(page);
}

function filterJobs() {
    loadJobs(1);
}

// ─── 清空筛选 ────────────────────────────
function clearFilters() {
    document.getElementById('searchBox').value = '';
    document.getElementById('cityFilter').value = '';
    document.getElementById('educationFilter').value = '';
    currentKeyword = '';
    currentCity = '';
    currentEducation = '';
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