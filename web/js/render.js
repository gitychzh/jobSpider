/**
 * render.js — 渲染职位卡片、统计面板、分页
 *
 * 增强功能：
 *  - 卡片hover更明显
 *  - 薪资标签高亮
 *  - 时间格式化
 *  - 更清晰的空状态提示
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

function formatDate(dateStr) {
    if (!dateStr) return '';
    // 只取日期部分
    return dateStr.slice(0, 10);
}

function formatRelativeTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    return formatDate(dateStr);
}

function highlightText(text, keyword) {
    if (!keyword || !text) return text || '';
    const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

function renderJobCard(job, keyword) {
    const salary = job.salary || '薪资面议';
    const workArea = job.work_area || '';
    const workYear = job.work_year || '经验不限';
    const education = job.education || '学历不限';
    const issueDate = formatDate(job.issue_date);
    const relativeTime = formatRelativeTime(job.issue_date);
    const confirmDate = formatDate(job.confirm_date);

    // 薪资颜色标签
    const salaryClass = salary === '薪资面议' ? 'salary-negotiable' : 'job-salary';

    // 经验和学历标签
    const tags = [];
    if (workYear !== '经验不限' && workYear !== '') {
        tags.push(`<span class="meta-tag">${workYear}</span>`);
    }
    if (education !== '学历不限' && education !== '') {
        tags.push(`<span class="meta-tag">${education}</span>`);
    }
    if (issueDate) {
        tags.push(`<span class="meta-tag date-tag" title="${job.issue_date}">${relativeTime}</span>`);
    }
    if (confirmDate && confirmDate !== issueDate) {
        tags.push(`<span class="meta-tag confirm-tag" title="确认时间: ${job.confirm_date}">✓${formatRelativeTime(job.confirm_date)}</span>`);
    }

    // 搜索关键词高亮
    const hlJobName = highlightText(job.job_name || '', keyword);
    const hlCompany = highlightText(job.company_name || '', keyword);
    const hlArea = highlightText(job.city || workArea, keyword);

    return `
    <div class="job-card" data-job-id="${job.job_id}">
        <div class="job-header">
            <div class="job-title">
                <a href="${job.job_url || '#'}" target="_blank" rel="noopener">${hlJobName}</a>
            </div>
            ${renderSourceTag(job.source)}
        </div>
        <div class="job-company">${hlCompany}</div>
        <div class="job-meta">
            <span class="${salaryClass}">${salary}</span>
            <span class="job-city-tag">${hlArea}</span>
            ${tags.join('')}
        </div>
    </div>`;
}

function renderJobList(jobs, keyword) {
    const el = document.getElementById('jobsList');
    if (!jobs || !jobs.length) {
        if (keyword) {
            el.innerHTML = `<div class="empty-box"><div class="icon">🔍</div><div class="msg">未找到匹配「${keyword}」的职位</div><div class="hint">试试其他关键词或切换城市</div></div>`;
        } else {
            el.innerHTML = `<div class="empty-box"><div class="icon">📭</div><div class="msg">暂无数据，等待爬取更新</div><div class="hint">数据每天自动更新</div></div>`;
        }
        return;
    }
    el.innerHTML = jobs.map(j => renderJobCard(j, keyword)).join('');
}

function renderStats(stats) {
    document.getElementById('totalJobs').textContent = stats.total_jobs || 0;
    document.getElementById('totalCompanies').textContent = stats.unique_companies || 0;
    document.getElementById('lastUpdate').textContent = stats.last_update || '-';

    const cityStats = document.getElementById('cityStats');
    if (stats.by_city) {
        // Show city stats as a bar-style visualization
        const entries = Object.entries(stats.by_city).sort((a, b) => b[1] - a[1]);
        const max = entries[0]?.[1] || 1;
        let parts = entries.map(([c, n]) => `${c}: ${n}`);
        cityStats.textContent = parts.join(' | ');
    }
}

function renderStatsPanel(stats) {
    // Render detailed stats panel below the header
    const panel = document.getElementById('statsPanel');
    if (!panel) return;

    if (!stats || !stats.total_jobs) {
        panel.innerHTML = '';
        return;
    }

    const educationData = stats.by_education || {};
    const salarySummary = stats.salary_summary || {};
    const cityData = stats.by_city || {};

    // Top 5 cities bar chart
    const topCities = Object.entries(cityData).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const cityMax = topCities[0]?.[1] || 1;

    let html = '<div class="stats-grid">';

    // City distribution
    html += '<div class="stats-section"><h3>城市分布</h3>';
    for (const [city, count] of topCities) {
        const pct = Math.round(count / cityMax * 100);
        html += `<div class="bar-row">
            <span class="bar-label">${city}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:var(--color-51job)"></div></div>
            <span class="bar-value">${count}</span>
        </div>`;
    }
    html += '</div>';

    // Education distribution
    const eduEntries = Object.entries(educationData).sort((a, b) => b[1] - a[1]);
    const eduMax = eduEntries[0]?.[1] || 1;
    if (eduEntries.length > 0) {
        html += '<div class="stats-section"><h3>学历要求</h3>';
        for (const [edu, count] of eduEntries.slice(0, 6)) {
            const pct = Math.round(count / eduMax * 100);
            html += `<div class="bar-row">
                <span class="bar-label">${edu || '不限'}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:#00b38a"></div></div>
                <span class="bar-value">${count}</span>
            </div>`;
        }
        html += '</div>';
    }

    // Salary summary
    html += '<div class="stats-section"><h3>薪资概要</h3>';
    html += `<div class="stat-item"><span class="stat-label">明确薪资</span><span class="stat-num">${salarySummary['有明确薪资'] || 0}条</span></div>`;
    html += `<div class="stat-item"><span class="stat-label">薪资面议</span><span class="stat-num">${salarySummary['面议'] || 0}条</span></div>`;
    html += '</div>';

    html += '</div>';
    panel.innerHTML = html;
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

    // 页面信息
    html += `<span class="page-info">${page}/${totalPages}</span>`;

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
    // Show skeleton cards for better perceived performance
    const skeletonCount = 5;
    let html = '';
    for (let i = 0; i < skeletonCount; i++) {
        html += `
        <div class="skeleton-card">
            <div class="skeleton-line title"></div>
            <div class="skeleton-line company"></div>
            <div class="skeleton-line meta"></div>
            <div class="skeleton-line short"></div>
        </div>`;
    }
    document.getElementById('jobsList').innerHTML = html;
    document.getElementById('pagination').innerHTML = '';
}