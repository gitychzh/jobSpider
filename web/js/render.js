/**
 * render.js — 渲染职位卡片、统计面板、分页
 */

const SOURCE_CONFIG = {
    job51:    { name: '51job',     color: '#1677ff', bg: '#e6f4ff',  label: '51job' },
    zhilian:  { name: '智联招聘',  color: '#f5222d', bg: '#fff1f0', label: '智联' },
    boss:     { name: 'Boss直聘',  color: '#00b38a', bg: '#e6fffb', label: 'Boss' },
};

function renderSourceTag(source) {
    const cfg = SOURCE_CONFIG[source] || { name: source, color: '#86909c', bg: '#f2f3f5' };
    return `<span class="source-tag ${source}" style="background:${cfg.bg};color:${cfg.color}">${cfg.name}</span>`;
}

function renderJobCard(job) {
    const salary = job.salary || '薪资面议';
    const workArea = job.work_area || '';
    const workYear = job.work_year || '经验不限';
    const education = job.education || '学历不限';
    const issueDate = (job.issue_date || '').slice(0, 10);  // Already in Beijing time

    return `
    <div class="job-card">
        <div class="job-header">
            <div class="job-title">
                <a href="${job.job_url || '#'}" target="_blank" rel="noopener">${job.job_name || ''}</a>
            </div>
            ${renderSourceTag(job.source)}
        </div>
        <div class="job-company">${job.company_name || ''}</div>
        <div class="job-meta">
            <span class="job-salary">${salary}</span>
            <span class="job-city-tag">${job.city || workArea}</span>
            ${workYear !== '经验不限' ? `<span>${workYear}</span>` : ''}
            ${education !== '学历不限' ? `<span>${education}</span>` : ''}
            ${issueDate ? `<span>${issueDate}</span>` : ''}
        </div>
    </div>`;
}

function renderJobList(jobs, keyword) {
    const el = document.getElementById('jobsList');
    if (!jobs || !jobs.length) {
        if (keyword) {
            el.innerHTML = `<div class="empty-box"><div class="icon">🔍</div><div class="msg">未找到匹配「${keyword}」的职位</div></div>`;
        } else {
            el.innerHTML = `<div class="empty-box"><div class="icon">📭</div><div class="msg">暂无数据，等待爬取更新</div></div>`;
        }
        return;
    }
    el.innerHTML = jobs.map(renderJobCard).join('');
}

function renderStats(stats) {
    document.getElementById('totalJobs').textContent = stats.total_jobs || 0;
    document.getElementById('totalCompanies').textContent = stats.unique_companies || 0;
    document.getElementById('lastUpdate').textContent = stats.last_update || '-';

    const cityStats = document.getElementById('cityStats');
    if (stats.by_city) {
        const parts = Object.entries(stats.by_city).map(([c, n]) => `${c}: ${n}`);
        cityStats.textContent = parts.join(' | ');
    }
}

function renderPagination(page, totalPages) {
    const el = document.getElementById('pagination');
    if (totalPages <= 1) { el.innerHTML = ''; return; }

    const maxShow = 5;
    let start = Math.max(1, page - Math.floor(maxShow / 2));
    let end = Math.min(totalPages, start + maxShow - 1);
    if (end - start + 1 < maxShow) start = Math.max(1, end - maxShow + 1);

    let html = '';
    if (page > 1) {
        html += `<button class="page-btn" onclick="loadPage(${page - 1})">上一页</button>`;
    } else {
        html += `<button class="page-btn disabled">上一页</button>`;
    }

    if (start > 1) {
        html += `<button class="page-btn" onclick="loadPage(1)">1</button>`;
        if (start > 2) html += `<span style="color:#999;padding:4px">…</span>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="loadPage(${i})">${i}</button>`;
    }

    if (end < totalPages) {
        if (end < totalPages - 1) html += `<span style="color:#999;padding:4px">…</span>`;
        html += `<button class="page-btn" onclick="loadPage(${totalPages})">${totalPages}</button>`;
    }

    if (page < totalPages) {
        html += `<button class="page-btn" onclick="loadPage(${page + 1})">下一页</button>`;
    } else {
        html += `<button class="page-btn disabled">下一页</button>`;
    }

    el.innerHTML = html;
}

function renderComingSoon(name) {
    const cfg = SOURCE_CONFIG[name] || { name: name };
    document.getElementById('jobsList').innerHTML = `
        <div class="coming-soon">
            <div class="icon">🚧</div>
            <div class="title">${cfg.name} 暂未开放</div>
            <div class="desc">该平台爬虫正在开发中，敬请期待</div>
        </div>`;
    document.getElementById('pagination').innerHTML = '';
}

function renderLoading() {
    document.getElementById('jobsList').innerHTML = `
        <div class="loading-box"><span class="spinner"></span><br>加载中...</div>`;
    document.getElementById('pagination').innerHTML = '';
}