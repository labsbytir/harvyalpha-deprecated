// Harvy Query Dashboard client
(function() {
  'use strict';

  const metricSelect = document.getElementById('metric-select');
  const sourceFilter = document.getElementById('source-filter');
  const runBtn = document.getElementById('run-query-btn');
  const resultsContainer = document.getElementById('query-results');
  const dashboardsList = document.getElementById('dashboards-list');
  const saveDashboardBtn = document.getElementById('save-dashboard-btn');

  let catalog = null;

  async function initCatalog() {
    try {
      const res = await fetch('/api/query/catalog');
      catalog = await res.json();
      metricSelect.innerHTML = catalog.metrics.map(m => 
        `<option value="${m.id}">${m.name} [${m.type}]</option>`
      ).join('');
      runQuery();
      loadDashboards();
    } catch (e) {
      console.error('Failed to load query catalog:', e);
      resultsContainer.innerHTML = `<div class="qn-card" style="color:var(--accent-red)">Failed to load query catalog.</div>`;
    }
  }

  async function runQuery() {
    const metric = metricSelect.value;
    const source = sourceFilter.value;
    const filters = {};
    if (source && source !== 'all') filters.source = source;

    resultsContainer.innerHTML = `<div class="qn-card" style="color:var(--text-muted)">Executing query...</div>`;

    try {
      const res = await fetch('/api/query/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric, filters })
      });
      const data = await res.json();
      if (data.error) {
        resultsContainer.innerHTML = `<div class="qn-card" style="color:var(--accent-red)">Error: ${data.error}</div>`;
        return;
      }
      renderResults(metric, data.results, data.environment);
    } catch (e) {
      resultsContainer.innerHTML = `<div class="qn-card" style="color:var(--accent-red)">Execution failed: ${e.message}</div>`;
    }
  }

  function renderResults(metricId, rows, env) {
    if (!rows || rows.length === 0) {
      resultsContainer.innerHTML = `
        <div class="qn-card">
          <div class="qn-card-title">${metricId} <span class="qn-tag">Scope: ${env}</span></div>
          <div style="color:var(--text-muted)">No matching records in scope.</div>
        </div>`;
      return;
    }

    // Scalar metric
    if (rows.length === 1 && rows[0].value !== undefined && rows[0].dimension === undefined) {
      resultsContainer.innerHTML = `
        <div class="qn-card">
          <div class="qn-card-title">${metricId} <span class="qn-tag">Scope: ${env}</span></div>
          <div class="qn-metric-card">
            <div class="qn-metric-val">${rows[0].value.toLocaleString()}</div>
            <div class="qn-metric-lbl">Current Scoped Count</div>
          </div>
        </div>`;
      return;
    }

    // Tabular / Distribution / Timeseries
    const trs = rows.map(r => `
      <tr>
        <td style="font-family:var(--font-mono)">${r.dimension || 'unknown'}</td>
        <td style="font-family:var(--font-mono);font-weight:600;color:var(--accent-blue)">${Number(r.value || 0).toLocaleString()}</td>
      </tr>
    `).join('');

    resultsContainer.innerHTML = `
      <div class="qn-card">
        <div class="qn-card-title">
          <span>${metricId}</span>
          <span class="qn-tag">Scope: ${env}</span>
        </div>
        <table class="qn-table">
          <thead>
            <tr>
              <th>DIMENSION</th>
              <th>VALUE</th>
            </tr>
          </thead>
          <tbody>
            ${trs}
          </tbody>
        </table>
      </div>`;
  }

  async function loadDashboards() {
    try {
      const res = await fetch('/api/dashboards');
      if (res.status === 401) {
        dashboardsList.innerHTML = `<div style="color:var(--text-subtle);font-size:12px;">Sign in to view saved dashboards.</div>`;
        return;
      }
      const data = await res.json();
      if (data.dashboards && data.dashboards.length > 0) {
        dashboardsList.innerHTML = data.dashboards.map(d => `
          <div style="padding:8px 0;border-bottom:1px solid var(--border)">
            <div style="font-weight:600;font-size:13px">${d.title}</div>
            <div style="font-size:11px;color:var(--text-muted)">${d.description || 'No description'}</div>
          </div>
        `).join('');
      } else {
        dashboardsList.innerHTML = `<div style="color:var(--text-subtle);font-size:12px;">No saved dashboards.</div>`;
      }
    } catch (e) {
      dashboardsList.innerHTML = `<div style="color:var(--text-subtle);font-size:12px;">Saved dashboards unavailable.</div>`;
    }
  }

  async function saveDashboard() {
    const title = prompt('Enter Dashboard Title:');
    if (!title) return;
    try {
      const res = await fetch('/api/dashboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: `Created for metric ${metricSelect.value}`,
          layout: { defaultMetric: metricSelect.value },
          queries: [{ metric: metricSelect.value, filters: { source: sourceFilter.value } }]
        })
      });
      if (res.status === 401) {
        alert('Please sign in to save dashboards.');
        return;
      }
      await loadDashboards();
    } catch (e) {
      alert('Failed to save dashboard: ' + e.message);
    }
  }

  runBtn.addEventListener('click', runQuery);
  metricSelect.addEventListener('change', runQuery);
  sourceFilter.addEventListener('change', runQuery);
  if (saveDashboardBtn) saveDashboardBtn.addEventListener('click', saveDashboard);

  initCatalog();
})();
