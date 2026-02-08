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

const SCENARIOS = {
  ba: {
    context: "We are an e-commerce company planning to expand our product line into high-end sustainable furniture. We currently sell standard office supplies and electronics.",
    task: "Analyze our current sales trends by region and product category. Based on the performance of our 'Furniture' category in the South and West regions, suggest 3 specific sustainable furniture products we should launch next quarter.",
    file: "sales_data.csv"
  },
  da: {
    context: "The management team wants a deep dive into our profit margins across different regions and product types.",
    task: "Perform an exploratory data analysis (EDA) to identify which product category is most profitable per unit. Create a visualization showing the profit distribution by region. Highlight any regions where sales are high but profit is low.",
    file: "sales_data.csv"
  },
  ml: {
    context: "We want to optimize our inventory by predicting future sales volume.",
    task: "Build a simple time-series forecasting model (or a regression model using date as a feature) to predict the total sales volume for the next 7 days. Use the existing data for training and evaluation. Print the Mean Absolute Error (MAE) and save a plot of historical vs. predicted sales.",
    file: "sales_data.csv"
  }
};

// Scenario selection
const scenarioSelect = document.getElementById('scenario-select');
scenarioSelect.addEventListener('change', () => {
  const key = scenarioSelect.value;
  if (key && SCENARIOS[key]) {
    document.getElementById('business-context').value = SCENARIOS[key].context;
    document.getElementById('task').value = SCENARIOS[key].task;

    if (!uploadedPath) {
      fileNameSpan.textContent = `Please upload ${SCENARIOS[key].file}`;
      fileNameSpan.classList.add('warning');
    }
  }
});

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

const toggleReport = document.getElementById('toggle-report');
const toggleCode = document.getElementById('toggle-code');
const reportView = document.getElementById('report-view');
const codeView = document.getElementById('code-view');

// Toggle logic
if (toggleReport && toggleCode) {
  toggleReport.addEventListener('click', () => {
    toggleReport.classList.add('active');
    toggleCode.classList.remove('active');
    if (reportView) reportView.classList.remove('hidden');
    if (codeView) codeView.classList.add('hidden');
  });

  toggleCode.addEventListener('click', () => {
    toggleReport.classList.remove('active');
    toggleCode.classList.add('active');
    if (reportView) reportView.classList.add('hidden');
    if (codeView) codeView.classList.remove('hidden');
  });
}

async function showResults(downloads) {
  const reportContainer = document.getElementById('report-container');
  const codeContainer = document.getElementById('code-container');

  resultsSection.classList.remove('hidden');
  resultsSection.classList.add('fadeIn');
  downloadsDiv.innerHTML = '';

  // Reset to report view by default when showing results
  if (toggleReport) toggleReport.click();

  if (reportContainer) reportContainer.innerHTML = 'Loading report...';
  if (codeContainer) codeContainer.textContent = 'Loading code...';

  if (downloads.report) {
    // 1. Render Markdown Report
    try {
      const response = await fetch(`${API_BASE}/download/${downloads.report}`);
      const markdown = await response.text();

      // Configure marked to resolve relative images correctly
      const sessionDir = downloads.report.split('/')[0];
      const renderer = new marked.Renderer();
      const originalImage = renderer.image.bind(renderer);
      renderer.image = (token) => {
        let href = typeof token === 'string' ? token : token.href;
        if (href && !href.startsWith('http') && !href.startsWith('/')) {
          href = `${API_BASE}/download/${sessionDir}/${href}`;
        }
        return originalImage(typeof token === 'string' ? href : { ...token, href });
      };

      reportContainer.innerHTML = marked.parse(markdown, { renderer });
    } catch (e) {
      reportContainer.innerHTML = `<p class="error">Failed to load report: ${e.message}</p>`;
    }

    // 2. Fetch and Highlight Code
    if (downloads.pipeline && codeContainer) {
      try {
        const response = await fetch(`${API_BASE}/download/${downloads.pipeline}`);
        const code = await response.text();
        codeContainer.textContent = code;
        Prism.highlightElement(codeContainer);
      } catch (e) {
        codeContainer.textContent = `Failed to load code: ${e.message}`;
      }
    }

    // 3. Add Download Buttons
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
  const metaData = document.getElementById('metaData').value.trim()
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
      metaData: metaData,
      file_paths: filePaths,
    }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        appendLog(data);
        if (data.agent) {
          if (data.message && data.message.includes('Agent started')) {
            setStatus(`Current Step: ${data.agent}`, 'running');
          }

          if (data.reason && typeof showReasoning === 'function') {
            showReasoning(data.agent, data.reason);
          }
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
    } catch (e) {
      console.error(e);
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