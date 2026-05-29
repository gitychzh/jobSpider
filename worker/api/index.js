/**
 * jobSpider API Worker — reads/writes D1, serves JSON to frontend
 * All timestamps in DB are Beijing time (UTC+8), returned as-is.
 */

const PER_PAGE = 50;
const VALID_SOURCES = ['job51', 'zhilian', 'boss'];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, X-Import-Secret',
        },
      });
    }

    if (path === '/api/jobs' && request.method === 'GET') return handleJobs(url, env);
    if (path === '/api/stats' && request.method === 'GET') return handleStats(url, env);
    if (path === '/api/sources' && request.method === 'GET') return handleSources(env);
    if (path === '/api/cities' && request.method === 'GET') return handleCities(url, env);
    if (path === '/api/import' && request.method === 'POST') return handleImport(request, env);
    if (path === '/api/cleanup' && request.method === 'POST') return handleCleanup(request, env);

    return new Response('Not found', { status: 404 });
  },
};

async function handleImport(request, env) {
  const secret = request.headers.get('X-Import-Secret');
  if (secret !== (env.IMPORT_SECRET || 'changeme-set-in-wrangler')) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { action, source, jobs } = body;

  if (action === 'insert_jobs' && jobs && jobs.length) {
    const stmts = [];
    for (const j of jobs) {
      stmts.push(
        env.DB.prepare(
          `INSERT OR REPLACE INTO jobs (job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, confirm_date, update_time, job_url, city, scrape_date, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
        ).bind(
          j.job_id, j.job_name, j.company_name, j.salary, j.work_area,
          j.work_year, j.education, j.issue_date, j.confirm_date, j.update_time,
          j.job_url, j.city, j.scrape_date, j.source
        )
      );
    }

    const batchSize = 100;
    let inserted = 0;
    for (let i = 0; i < stmts.length; i += batchSize) {
      const batch = stmts.slice(i, i + batchSize);
      const result = await env.DB.batch(batch);
      inserted += batch.length;
    }

    return jsonResponse({ success: true, inserted });
  }

  if (action === 'log_scrape_run') {
    const { status, total_jobs, error_msg } = body;
    await env.DB.prepare(
      `INSERT INTO scrape_runs (source, status, total_jobs, started_at, completed_at, error_msg) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)`
    ).bind(source, status, total_jobs || 0, body.started_at || '', error_msg || '').run();

    return jsonResponse({ success: true });
  }

  return jsonResponse({ error: 'Invalid action' }, 400);
}

async function handleCleanup(request, env) {
  const secret = request.headers.get('X-Import-Secret');
  if (secret !== (env.IMPORT_SECRET || 'changeme-set-in-wrangler')) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const body = await request.json();
  const { source, keep_days } = body;

  if (!source || !VALID_SOURCES.includes(source)) {
    return jsonResponse({ error: 'Invalid source' }, 400);
  }

  const days = keep_days || 30;
  const result = await env.DB.prepare(
    `DELETE FROM jobs WHERE source = ? AND scrape_date < date('now', '-' || ? || ' days')`
  ).bind(source, days).run();

  return jsonResponse({ success: true, deleted: result.meta?.changes || 0 });
}

async function handleJobs(url, env) {
  const source = url.searchParams.get('source') || 'job51';
  const page = parseInt(url.searchParams.get('page') || '1');
  const city = url.searchParams.get('city') || '';
  const keyword = url.searchParams.get('keyword') || '';
  const sortField = url.searchParams.get('sortField') || 'issue_date';
  const sortOrder = url.searchParams.get('sortOrder') || 'desc';

  if (!VALID_SOURCES.includes(source)) {
    return jsonResponse({ error: 'Invalid source' }, 400);
  }

  let whereClauses = [`source = ?`];
  let params = [source];

  if (city) {
    whereClauses.push(`city = ?`);
    params.push(city);
  }
  if (keyword) {
    whereClauses.push(`(job_name LIKE ? OR company_name LIKE ?)`);
    params.push(`%${keyword}%`, `%${keyword}%`);
  }

  const where = whereClauses.join(' AND ');
  const order = `ORDER BY ${sortField} ${sortOrder === 'desc' ? 'DESC' : 'ASC'}`;
  const offset = (page - 1) * PER_PAGE;

  const countResult = await env.DB.prepare(
    `SELECT COUNT(*) as total FROM jobs WHERE ${where}`
  ).bind(...params).first();

  const total = countResult?.total || 0;

  const jobsResult = await env.DB.prepare(
    `SELECT job_id, job_name, company_name, salary, work_area, work_year, education, issue_date, confirm_date, update_time, job_url, city, scrape_date, source FROM jobs WHERE ${where} ${order} LIMIT ? OFFSET ?`
  ).bind(...params, PER_PAGE, offset).all();

  const displayNames = { job51: '51job', zhilian: '智联招聘', boss: 'Boss直聘' };

  return jsonResponse({
    source,
    display_name: displayNames[source] || source,
    total,
    page,
    per_page: PER_PAGE,
    total_pages: Math.max(1, Math.ceil(total / PER_PAGE)),
    jobs: (jobsResult.results || []),
  });
}

async function handleStats(url, env) {
  const source = url.searchParams.get('source') || 'job51';

  const totalResult = await env.DB.prepare(
    `SELECT COUNT(*) as total_jobs, COUNT(DISTINCT company_name) as unique_companies FROM jobs WHERE source = ?`
  ).bind(source).first();

  const citiesResult = await env.DB.prepare(
    `SELECT city, COUNT(*) as count FROM jobs WHERE source = ? AND city != '' GROUP BY city ORDER BY count DESC`
  ).bind(source).all();

  const lastUpdate = await env.DB.prepare(
    `SELECT MAX(scrape_date) as last_update FROM jobs WHERE source = ?`
  ).bind(source).first();

  const displayNames = { job51: '51job', zhilian: '智联招聘', boss: 'Boss直聘' };

  return jsonResponse({
    source,
    display_name: displayNames[source] || source,
    total_jobs: totalResult?.total_jobs || 0,
    unique_companies: totalResult?.unique_companies || 0,
    by_city: Object.fromEntries(
      (citiesResult.results || []).map(r => [r.city, r.count])
    ),
    last_update: lastUpdate?.last_update || '',
  });
}

async function handleSources(env) {
  const results = await env.DB.prepare(
    `SELECT source, COUNT(*) as total_jobs FROM jobs GROUP BY source`
  ).all();

  const displayNames = { job51: '51job', zhilian: '智联招聘', boss: 'Boss直聘' };

  const available = VALID_SOURCES.map(s => {
    const row = (results.results || []).find(r => r.source === s);
    return {
      source: s,
      display_name: displayNames[s] || s,
      available: !!row,
      total_jobs: row?.total_jobs || 0,
    };
  });

  const lastUpdate = await env.DB.prepare(
    `SELECT MAX(scrape_date) as last_update FROM jobs`
  ).first();

  return jsonResponse({
    last_update: lastUpdate?.last_update || '',
    available_sources: available.filter(s => s.available).map(s => s.source),
    sources: available,
  });
}

async function handleCities(url, env) {
  const source = url.searchParams.get('source') || 'job51';

  const result = await env.DB.prepare(
    `SELECT city, COUNT(*) as count FROM jobs WHERE source = ? AND city != '' GROUP BY city ORDER BY count DESC`
  ).bind(source).all();

  return jsonResponse((result.results || []));
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'max-age=300',
    },
  });
}