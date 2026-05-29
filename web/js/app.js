/**
 * app.js — 主逻辑：从 Cloudflare D1 API 加载数据，搜索、筛选、分页、平台切换
 */
const PER_PAGE = 50;
const API_BASE = 'https://jobspider-api.93921526.workers.dev';

const AVAILABLE_SOURCES = ['job51', 'zhilian', 'boss'];

let currentSource = 'job51';
let currentPage = 1;
let currentKeyword = '';
let currentCity = '';
let sourceDataCache = {};  // Cache total counts per source

// ─── 平台切换 ────────────────────────────
function switchSource(source) {
    currentSource = source;
    currentPage = 1;
    currentKeyword = '';
    currentCity = '';

    document.getElementById('searchBox').value = '';
    document.getElementById('cityFilter').value = '';

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
async function updateCityFilter(source) {
    const sel = document.getElementById('cityFilter');
    sel.innerHTML = '<option value="">全部城市</option>';

    try {
        const res = await fetch(`${API_BASE}/api/cities?source=${source}`);
        if (!res.ok) return;
        const cities = await res.json();
        cities.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.city;
            opt.textContent = `${c.city} (${c.count})`;
            sel.appendChild(opt);
        });
    } catch (e) {
        // Fallback: try from cache
        const data = sourceDataCache[source];
        if (data && data.by_city) {
            Object.entries(data.by_city).sort((a, b) => b[1] - a[1]).forEach(([c, n]) => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = `${c} (${n})`;
                sel.appendChild(opt);
            });
        }
    }
}

// ─── 数据加载 ────────────────────────────
async function loadJobs(page) {
    currentPage = page;
    currentCity = document.getElementById('cityFilter').value;
    currentKeyword = document.getElementById('searchBox').value.trim();

    renderLoading();

    const params = new URLSearchParams({
        source: currentSource,
        page: page,
    });
    if (currentCity) params.set('city', currentCity);
    if (currentKeyword) params.set('keyword', currentKeyword);
    params.set('sortField', document.getElementById('sortField').value || 'issue_date');
    params.set('sortOrder', document.getElementById('sortOrder').value || 'desc');

    try {
        const res = await fetch(`${API_BASE}/api/jobs?${params}`);
        if (!res.ok) {
            if (res.status === 400) {
                renderComingSoon(currentSource);
                return;
            }
            throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();

        if (!data.jobs || data.jobs.length === 0 && page === 1 && !currentCity && !currentKeyword) {
            renderComingSoon(currentSource);
            return;
        }

        renderJobList(data.jobs, currentKeyword);
        renderPagination(data.page, data.total_pages);
        updateCityFilter(currentSource);
        loadStats(currentSource);
    } catch (e) {
        console.error('Failed to load jobs:', e);
        document.getElementById('jobsList').innerHTML = `
            <div class="empty-box"><div class="icon">⚠️</div><div class="msg">加载失败，请稍后重试</div></div>`;
    }
}

async function loadStats(source) {
    try {
        const res = await fetch(`${API_BASE}/api/stats?source=${source}`);
        if (!res.ok) return;
        const stats = await res.json();
        sourceDataCache[source] = stats;
        renderStats(stats);
    } catch (e) {
        // 忽略
    }
}

function loadPage(page) {
    loadJobs(page);
}

function filterJobs() {
    loadJobs(1);
}

// ─── 初始化 ────────────────────────────
async function init() {
    try {
        const res = await fetch(`${API_BASE}/api/sources`);
        if (res.ok) {
            const data = await res.json();
            const availableSet = new Set(data.available_sources);

            for (const src of AVAILABLE_SOURCES) {
                if (SOURCE_CONFIG[src]) {
                    SOURCE_CONFIG[src].available = availableSet.has(src);
                }
            }

            document.querySelectorAll('.tab-btn').forEach(btn => {
                const src = btn.dataset.source;
                if (src && SOURCE_CONFIG[src] && !SOURCE_CONFIG[src].available) {
                    btn.classList.add('disabled');
                }
            });
        }
    } catch (e) {
        // Fallback: assume job51 is available
        console.warn('Failed to load sources, using defaults');
    }

    switchSource('job51');

    document.getElementById('searchBox').addEventListener('keypress', e => {
        if (e.key === 'Enter') filterJobs();
    });
}

document.addEventListener('DOMContentLoaded', init);