'use strict';
const $ = (id) => document.getElementById(id);
let job = null;
let timer = null;
let polling = false;

function message(text, isError = false) {
  $('research-message').textContent = text;
  $('research-message').dataset.error = isError ? 'true' : 'false';
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
    let error = `Request failed (${response.status}).`;
    try { error = (await response.json()).error || error; } catch (_) {}
    throw new Error(error);
  }
  return blob ? response.blob() : response.json();
}

function busy(value) {
  for (const id of ['legal-query', 'first-name', 'last-name', 'arrest-state', 'latitude', 'longitude', 'legal-consent', 'map-consent', 'legal-start', 'map-start']) {
    $(id).disabled = value;
  }
  document.querySelectorAll('[name="source"]').forEach((el) => { el.disabled = value; });
  $('research-stop').disabled = !value;
}

async function startJob(payload) {
  if (!accessToken) throw new Error('Enter the Harvy workspace token above.');
  job = await api('/api/research-jobs', {method: 'POST', body: JSON.stringify({...payload, consent: true})});
  $('research-state').textContent = 'RUNNING';
  $('research-state').dataset.state = 'running';
  $('research-log').hidden = false;
  $('research-download').disabled = true;
  busy(true);
  clearInterval(timer);
  timer = setInterval(poll, 1500);
  await poll();
}

async function poll() {
  if (!job || polling) return;
  polling = true;
  try {
    const data = await api(`/api/jobs/${job.id}`);
    const running = data.status === 'running';
    $('research-state').textContent = data.status.toUpperCase();
    $('research-state').dataset.state = data.status;
    $('research-log').textContent = data.logs.join('') || 'Worker started…';
    $('research-log').scrollTop = $('research-log').scrollHeight;
    message(running ? 'Harvy is checking the selected public sources…' :
      'Finished. Review the report and verify candidate records at their originating sources.');
    busy(running);
    if (!running) {
      clearInterval(timer);
      $('research-download').disabled = data.files.length === 0;
      const list = $('research-files');
      list.replaceChildren();
      for (const file of data.files) {
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = ({
          'raw/courtlistener.json': 'Case Intelligence',
          'raw/case_law.json': 'Legal Opinions',
          'raw/judyrecords.json': 'Public Records',
          'raw/arrests_org.json': 'Public Records',
          'raw/docket_alarm.json': 'Docket Intelligence',
          'raw/mapillary.json': 'Location Intelligence',
          'research-report.json': 'Harvy Research Report',
        })[file.path] || 'Harvy Research Artifact';
        button.addEventListener('click', () => download(
          `/api/jobs/${job.id}/files/${file.path.split('/').map(encodeURIComponent).join('/')}`,
          file.path.split('/').pop()));
        item.append(button);
        list.append(item);
      }
      if (!job.searchIndexed) {
        try {
          const searchData = await api(`/api/jobs/${job.id}/search-documents`);
          window.HarvyDataSearch.load(searchData.documents, searchData.truncated);
          job.searchIndexed = true;
        } catch (error) { message(`Search index could not be built: ${error.message}`, true); }
      }
    }
  } catch (error) {
    message(`${error.message} Progress will retry while this page remains open.`, true);
  } finally { polling = false; }
}

async function download(path, filename) {
  try {
    const blob = await api(path, {}, true);
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  } catch (error) { message(error.message, true); }
}

$('legal-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  message('Starting legal search…');
  try {
    await startJob({
      mode: 'legal',
      query: $('legal-query').value.trim(),
      first_name: $('first-name').value.trim(),
      last_name: $('last-name').value.trim(),
      state: $('arrest-state').value,
      sources: [...document.querySelectorAll('[name="source"]:checked')].map((el) => el.value),
    });
  } catch (error) { message(error.message, true); busy(false); }
});

$('map-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  message('Starting imagery lookup…');
  try {
    await startJob({mode: 'map', latitude: Number($('latitude').value), longitude: Number($('longitude').value)});
  } catch (error) { message(error.message, true); busy(false); }
});

$('research-stop').addEventListener('click', async () => {
  if (!job) return;
  try { await api(`/api/jobs/${job.id}/stop`, {method: 'POST'}); await poll(); }
  catch (error) { message(error.message, true); }
});

$('research-download').addEventListener('click', () => {
  if (job) download(`/api/jobs/${job.id}/download`, `harvy-research-${job.id.slice(0, 8)}.zip`);
});
