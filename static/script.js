/**
 * ML Agent Forge - Frontend
 * Handles file upload, WebSocket run, live logs, and downloads.
 */

const API_BASE = '';

// DOM elements
const form = document.getElementById('run-form');
const runBtn = document.getElementById('run-btn');
const fileInput = document.getElementById('file-input');
const fileNameSpan = document.getElementById('file-name');
const statusValue = document.getElementById('status-value');
const logContent = document.getElementById('log-content');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const downloadsDiv = document.getElementById('downloads');

let uploadedPath = null;

// File selection
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) {
    fileNameSpan.textContent = file.name;
    uploadFile(file);
  } else {
    fileNameSpan.textContent = 'No file selected';
    uploadedPath = null;
  }
});

async function uploadFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd });
    const data = await r.json();
    uploadedPath = data.filename;
    fileNameSpan.textContent = `${file.name} (uploaded)`;
  } catch (e) {
    fileNameSpan.textContent = `Upload failed: ${e.message}`;
    uploadedPath = null;
  }
}

function appendLog(ev) {
  const pre = logContent;
  const line = document.createElement('div');
  line.className = 'log-line';

  const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';
  const agent = ev.agent ? `[${ev.agent}]` : '';
  const msg = ev.message || JSON.stringify(ev);
  const level = ev.level || 'info';

  line.innerHTML = `<span class="ts">${ts}</span> <span class="agent">${agent}</span> <span class="level-${level}">${msg}</span>`;
  pre.appendChild(line);
  const logWindow = document.getElementById('log-window');
  if (logWindow) logWindow.scrollTop = logWindow.scrollHeight;
}

function setStatus(text, className = '') {
  statusValue.textContent = text;
  statusValue.className = 'status-value ' + className;
}

function showResults(downloads) {
  resultsSection.classList.remove('hidden');
  downloadsDiv.innerHTML = '';
  if (downloads.report) {
    const a = document.createElement('a');
    a.href = `${API_BASE}/download/${downloads.report}`;
    a.download = 'final_report.md';
    a.className = 'btn';
    a.textContent = 'Download Report (.md)';
    a.click = () => {};
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = 'Download Report (.md)';
    btn.onclick = () => window.open(`${API_BASE}/download/${downloads.report}`, '_blank');
    downloadsDiv.appendChild(btn);
  }
  if (downloads.pipeline) {
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = 'Download Code / Pipeline';
    btn.onclick = () => window.open(`${API_BASE}/download/${downloads.pipeline}`, '_blank');
    downloadsDiv.appendChild(btn);
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const businessContext = document.getElementById('business-context').value.trim();
  const task = document.getElementById('task').value.trim();
  const filePaths = uploadedPath ? [uploadedPath] : [];

  runBtn.disabled = true;
  setStatus('Connecting...', 'running');
  logContent.innerHTML = '';

  const wsUrl = `${(window.location.protocol === 'https:' ? 'wss:' : 'ws:')}//${window.location.host}${API_BASE}/ws/run`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    setStatus('Running pipeline...', 'running');
    ws.send(JSON.stringify({
      business_context: businessContext,
      task,
      file_paths: filePaths,
    }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        appendLog(data);
        if (data.agent && data.message && data.message.includes('Agent started')) {
          setStatus(`Current Step: ${data.agent}`, 'running');
        }
      } else if (data.type === 'done') {
        setStatus('Done', 'done');
        showResults(data.downloads || {});
        runBtn.disabled = false;
      } else if (data.type === 'error') {
        setStatus(`Error: ${data.message}`, 'error');
        appendLog({ message: data.message, level: 'error' });
        runBtn.disabled = false;
      }
    } catch (_) {
      appendLog({ message: event.data, level: 'info' });
    }
  };

  ws.onerror = () => {
    setStatus('Connection error', 'error');
    runBtn.disabled = false;
  };

  ws.onclose = () => {
    if (runBtn.disabled && statusValue.textContent.includes('Running')) {
      setStatus('Connection closed', 'error');
      runBtn.disabled = false;
    }
  };
});
