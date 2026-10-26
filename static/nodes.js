// Harvy Nodes Graph Visualization & Provenance Client
(function() {
  'use strict';

  const canvas = document.getElementById('nodes-canvas');
  const ctx = canvas.getContext('2d');
  const sidebar = document.getElementById('nodes-sidebar');
  const viewToggleBtn = document.getElementById('toggle-view-btn');
  const canvasWrap = document.getElementById('canvas-wrap');
  const tableWrap = document.getElementById('table-wrap');
  const nodesTableBody = document.getElementById('nodes-table-body');
  const linksTableBody = document.getElementById('links-table-body');
  const envBadge = document.getElementById('env-badge');
  const countBadge = document.getElementById('count-badge');

  let width = 0;
  let height = 0;
  let graphData = { nodes: [], links: [] };
  let nodeMap = new Map();
  let selectedNode = null;
  let isTableView = false;

  // Viewport pan/zoom
  let transform = { x: 0, y: 0, scale: 1 };
  let isDragging = false;
  let dragNode = null;
  let startX = 0;
  let startY = 0;

  function resize() {
    width = canvasWrap.clientWidth;
    height = canvasWrap.clientHeight;
    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    render();
  }

  async function loadGraph() {
    try {
      const res = await fetch('/api/nodes/graph?limit=100');
      graphData = await res.json();
      envBadge.textContent = `Scope: ${graphData.environment}`;
      countBadge.textContent = `${graphData.total_nodes} nodes / ${graphData.total_links} links`;

      nodeMap.clear();
      const cx = width / 2;
      const cy = height / 2;

      graphData.nodes.forEach((n, i) => {
        const angle = (i / graphData.nodes.length) * Math.PI * 2;
        const radius = Math.min(width, height) * 0.35 * (0.4 + 0.6 * Math.random());
        n.x = cx + Math.cos(angle) * radius;
        n.y = cy + Math.sin(angle) * radius;
        n.vx = 0;
        n.vy = 0;
        nodeMap.set(n.id, n);
      });

      render();
      populateTables();
    } catch (e) {
      console.error('Failed to load nodes graph:', e);
    }
  }

  function simulate() {
    // Simple spring repulsion/attraction step
    const kRepel = 800;
    const kSpring = 0.05;
    const nodes = graphData.nodes;
    const links = graphData.links;

    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        if (dist < 300) {
          const force = kRepel / (dist * dist);
          nodes[i].vx += (dx / dist) * force;
          nodes[i].vy += (dy / dist) * force;
          nodes[j].vx -= (dx / dist) * force;
          nodes[j].vy -= (dy / dist) * force;
        }
      }
    }

    // Springs
    links.forEach(l => {
      const s = nodeMap.get(l.source);
      const t = nodeMap.get(l.target);
      if (s && t) {
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 120) * kSpring;
        s.vx += (dx / dist) * force;
        s.vy += (dy / dist) * force;
        t.vx -= (dx / dist) * force;
        t.vy -= (dy / dist) * force;
      }
    });

    // Damping & application
    nodes.forEach(n => {
      if (n !== dragNode) {
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
      }
    });
  }

  function render() {
    if (!ctx) return;
    simulate();

    ctx.save();
    ctx.clearRect(0, 0, width, height);

    ctx.translate(transform.x, transform.y);
    ctx.scale(transform.scale, transform.scale);

    // Draw Links
    graphData.links.forEach(l => {
      const s = nodeMap.get(l.source);
      const t = nodeMap.get(l.target);
      if (s && t) {
        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.stroke();

        // Midpoint label for link type
        const mx = (s.x + t.x) / 2;
        const my = (s.y + t.y) / 2;
        ctx.fillStyle = '#6e7681';
        ctx.font = '9px monospace';
        ctx.fillText(l.link_type, mx + 4, my);
      }
    });

    // Draw Nodes
    graphData.nodes.forEach(n => {
      const isSel = selectedNode && selectedNode.id === n.id;
      ctx.beginPath();
      ctx.arc(n.x, n.y, isSel ? 12 : 8, 0, Math.PI * 2);

      let color = '#58a6ff'; // default blue
      if (n.type === 'profile') color = '#3fb950'; // green
      else if (n.type === 'post') color = '#d29922'; // gold
      else if (n.type === 'document') color = '#8b949e';

      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = isSel ? 3 : 1.5;
      ctx.strokeStyle = isSel ? '#ffffff' : '#161b22';
      ctx.stroke();

      // Node label
      ctx.fillStyle = isSel ? '#ffffff' : '#c9d1d9';
      ctx.font = isSel ? 'bold 12px sans-serif' : '11px sans-serif';
      ctx.fillText(n.name || n.id, n.x + 12, n.y + 4);
    });

    ctx.restore();
    requestAnimationFrame(render);
  }

  async function inspectObject(urn) {
    try {
      const res = await fetch(`/api/ontology/objects/${encodeURIComponent(urn)}`);
      const data = await res.json();
      if (data.error) return;

      const obj = data.object;
      const obs = data.observations || [];

      sidebar.style.display = 'block';
      sidebar.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
          <div>
            <div style="font-weight:600;font-size:14px">${obj.display_name}</div>
            <div style="font-family:var(--font-mono);color:var(--accent-blue);font-size:11px">${obj.id}</div>
          </div>
          <button id="close-sidebar-btn" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;">&times;</button>
        </div>
        <div style="margin-bottom:12px">
          <span class="qn-tag">${obj.type_id}</span>
          ${obj.canonical_url ? `<a href="${obj.canonical_url}" target="_blank" rel="noopener" style="color:var(--accent-blue);font-size:11px;margin-left:8px">Open Source &rarr;</a>` : ''}
        </div>
        <div style="font-weight:600;font-size:11px;color:var(--text-subtle);margin-bottom:8px">OBSERVATION PROVENANCE (${obs.length})</div>
        ${obs.map(o => `
          <div style="background:var(--panel-bg);border:1px solid var(--border);border-radius:4px;padding:8px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:10px;color:var(--text-muted)">
              <span>${o.source}</span>
              <span>${new Date(o.observed_at * 1000).toISOString().slice(0, 10)}</span>
            </div>
            <div style="font-family:var(--font-mono);font-size:10px;color:var(--accent-amber);margin-top:4px;word-break:break-all">
              R2: ${o.r2_object_key || 'embedded'}
            </div>
          </div>
        `).join('')}
      `;

      document.getElementById('close-sidebar-btn').addEventListener('click', () => {
        sidebar.style.display = 'none';
        selectedNode = null;
      });
    } catch (e) {
      console.error('Provenance fetch failed:', e);
    }
  }

  function populateTables() {
    nodesTableBody.innerHTML = graphData.nodes.map(n => `
      <tr>
        <td style="font-family:var(--font-mono)">${n.id}</td>
        <td><span class="qn-tag">${n.type}</span></td>
        <td>${n.name}</td>
        <td>${n.url ? `<a href="${n.url}" target="_blank" rel="noopener" style="color:var(--accent-blue)">Link</a>` : '-'}</td>
      </tr>
    `).join('');

    linksTableBody.innerHTML = graphData.links.map(l => `
      <tr>
        <td style="font-family:var(--font-mono)">${l.source}</td>
        <td><span class="qn-tag">${l.link_type}</span></td>
        <td style="font-family:var(--font-mono)">${l.target}</td>
        <td>${(l.confidence * 100).toFixed(0)}%</td>
        <td style="font-family:var(--font-mono);font-size:10px">${l.evidence_id || '-'}</td>
      </tr>
    `).join('');
  }

  // Mouse Interaction
  canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - transform.x) / transform.scale;
    const my = (e.clientY - rect.top - transform.y) / transform.scale;

    for (let i = graphData.nodes.length - 1; i >= 0; i--) {
      const n = graphData.nodes[i];
      const dx = n.x - mx;
      const dy = n.y - my;
      if (dx * dx + dy * dy < 144) {
        dragNode = n;
        selectedNode = n;
        inspectObject(n.id);
        return;
      }
    }

    isDragging = true;
    startX = e.clientX - transform.x;
    startY = e.clientY - transform.y;
  });

  window.addEventListener('mousemove', e => {
    if (dragNode) {
      const rect = canvas.getBoundingClientRect();
      dragNode.x = (e.clientX - rect.left - transform.x) / transform.scale;
      dragNode.y = (e.clientY - rect.top - transform.y) / transform.scale;
    } else if (isDragging) {
      transform.x = e.clientX - startX;
      transform.y = e.clientY - startY;
    }
  });

  window.addEventListener('mouseup', () => {
    dragNode = null;
    isDragging = false;
  });

  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    transform.scale = Math.min(Math.max(0.2, transform.scale * factor), 4.0);
  });

  viewToggleBtn.addEventListener('click', () => {
    isTableView = !isTableView;
    if (isTableView) {
      canvasWrap.style.display = 'none';
      tableWrap.style.display = 'block';
      viewToggleBtn.textContent = 'View Graph Canvas';
    } else {
      canvasWrap.style.display = 'block';
      tableWrap.style.display = 'none';
      viewToggleBtn.textContent = 'View Accessible Table';
      resize();
    }
  });

  window.addEventListener('resize', resize);
  resize();
  loadGraph();
})();
