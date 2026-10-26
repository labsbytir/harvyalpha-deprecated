'use strict';
const $ = (id) => document.getElementById(id);
let job = null;
let timer = null;
let busy = false;

function showError(message) {
  $('form-error').textContent = message;
  $('form-error').hidden = !message;
}

async function api(path, options = {}, blob = false) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(job ? {'X-Job-Token': job.job_token} : {}),
      ...(options.body ? {'Content-Type': 'application/json'} : {}),
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { message = (await response.json()).error || message; } catch (_) {}
    throw new Error(message);
  }
  return blob ? response.blob() : response.json();
}

function setRunning(running) {
  $('start').disabled = running;
  $('start-username').disabled = running;
  $('stop').disabled = !running;
  for (const id of ['profile-url', 'max-posts', 'max-linked', 'consent', 'wmn-username', 'wmn-consent']) {
    $(id).disabled = running;
  }
  document.querySelectorAll('[name="wmn-category"]').forEach((input) => { input.disabled = running; });
}

async function download(path, name) {
  showError('');
  try {
    const blob = await api(path, {}, true);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { showError(error.message); }
}

async function poll() {
  if (!job || busy) return;
  busy = true;
  try {
    const data = await api(`/api/jobs/${job.id}`);
    const running = data.status === 'running';
    $('state').textContent = data.status === 'finished' ? 'Collected · partial' : data.status.replace('_', ' ');
    $('state').dataset.state = data.status;
    $('post-count').textContent = data.post_files;
    $('artifact-caption').textContent = job.kind === 'username' ? 'USERNAME CANDIDATES' : 'POST ARTIFACTS';
    if (job.kind === 'username') $('post-count').textContent = data.matches;
    $('file-count').textContent = data.files.length;
    $('elapsed').textContent = `${Math.floor(data.elapsed / 60)}m ${data.elapsed % 60}s`;
    $('log').textContent = data.logs.join('') || 'Worker started. Waiting for the first response…';
    $('log').scrollTop = $('log').scrollHeight;
    $('job-message').textContent = running ? (job.kind === 'username' ? 'Checking selected public sites through the cloud API…' : 'Collecting anonymously through the cloud API…') : (
      data.status === 'finished' ? 'Worker finished. Check the manifest for coverage and missing records.' :
      'Worker stopped or failed. Partial evidence has been kept; already-sent cloud requests may still finish.');
    setRunning(running);
    if (!running) {
      clearInterval(timer);
      $('download').disabled = data.files.length === 0;
      $('results').hidden = data.files.length === 0;
      $('file-list').replaceChildren();
      for (const file of data.files) {
        const row = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = file.path;
        button.addEventListener('click', () => download(
          `/api/jobs/${job.id}/files/${file.path.split('/').map(encodeURIComponent).join('/')}`,
          file.path.split('/').pop()));
        const size = document.createElement('small');
        size.textContent = `${(file.size / 1024).toFixed(1)} KB`;
        row.append(button, size);
        $('file-list').append(row);
      }
      if (!job.searchIndexed) {
        try {
          const searchData = await api(`/api/jobs/${job.id}/search-documents`);
          window.HarvyDataSearch.load(searchData.documents, searchData.truncated);
          job.searchIndexed = true;
        } catch (error) {
          showError(`Search index could not be built: ${error.message}`);
        }
      }
    }
  } catch (error) {
    showError(`${error.message} Progress will retry while this page remains open.`);
    $('stop').disabled = false;
  } finally { busy = false; }
}

$('scrape-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  showError('');
  $('start').disabled = true;
  try {
    job = await api('/api/jobs', {method: 'POST', body: JSON.stringify({
      url: $('profile-url').value.trim(),
      max_posts: Number($('max-posts').value),
      max_linked: Number($('max-linked').value),
      consent: $('consent').checked,
    })});
    clearInterval(timer);
    $('empty-state').hidden = true;
    $('log').hidden = false;
    $('results').hidden = true;
    $('download').disabled = true;
    $('state').textContent = 'Running';
    $('state').dataset.state = 'running';
    setRunning(true);
    timer = setInterval(poll, 1500);
    await poll();
  } catch (error) {
    showError(error.message);
    $('start').disabled = false;
  }
});

$('username-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  showError('');
  $('start-username').disabled = true;
  const categories = [...document.querySelectorAll('[name="wmn-category"]:checked')].map((input) => input.value);
  try {
    job = await api('/api/username-jobs', {method: 'POST', body: JSON.stringify({
      username: $('wmn-username').value.trim(),
      categories,
      consent: $('wmn-consent').checked,
    })});
    clearInterval(timer);
    $('empty-state').hidden = true;
    $('log').hidden = false;
    $('results').hidden = true;
    $('download').disabled = true;
    $('state').textContent = 'Running';
    $('state').dataset.state = 'running';
    setRunning(true);
    timer = setInterval(poll, 1500);
    await poll();
  } catch (error) {
    showError(error.message);
    $('start-username').disabled = false;
  }
});

$('stop').addEventListener('click', async () => {
  if (!job) return;
  $('stop').disabled = true;
  try { await api(`/api/jobs/${job.id}/stop`, {method: 'POST'}); await poll(); }
  catch (error) { showError(error.message); $('stop').disabled = false; }
});
$('download').addEventListener('click', () => {
  if (job) download(`/api/jobs/${job.id}/download`, `harvy-${job.id.slice(0, 8)}.json`);
});
